#!/usr/bin/ python3
# -*- coding: utf-8 -*-

from socket import *
import re


class ClientCmd():
    def __init__(self, ip, port):
        self.valid_cmd_set = ['USER', 'PASS', 'RETR', 'STOR', 'QUIT', 'SYST', 'TYPE', 'REST',
        'PORT', 'PASV', 'MKD', 'CWD', 'PWD', 'LIST', 'RMD', 'RNFR', 'RNTO', 'ABOR']
        self.client_ip = ip
        self.client_port = port
        self.BUFSIZE = 4096
        self.transfer_mode = ''
        self.filesize = 0
        self.total_write = 0
        self.file_ip = ''
        self.file_port = -1
        self.cli_sock = socket(AF_INET, SOCK_STREAM)

    def parseInput(self, user_input):
        '''Parse user input into command and param'''
        space_idx = user_input.find(' ')
        if space_idx != -1:
            command = user_input[:space_idx]
            param = user_input[space_idx+1:]
        else:
            command = user_input
            param = ''
        return command, param

    def initConnection(self):
        '''Start connection'''
        out_msg = ''
        try:
            self.cli_sock.connect((self.client_ip, self.client_port))
            response = self.cli_sock.recv(self.BUFSIZE)
            out_msg += '< '
            out_msg += str(response, encoding='utf8')
        except Exception:
            out_msg += '# Error: Connection time out\n'
        finally:
            return out_msg
            
    def getLocalIP(self):
        '''Return local ip, 127.0.0.1 most of the time'''
        '''If real ip needed try to uncomment this block'''
        ip = '127.0.0.1'
        # try:
        #     s = socket(AF_INET, SOCK_DGRAM)
        #     s.connect(('8.8.8.8', 80))
        #     ip = s.getsockname()[0]
        # finally:
        #     s.close()
        return ip

    def parseResponse(self, response):
        '''Parse server response to state code and message'''
        state_code = response[:3]
        msg = response[3:]
        try:
            state_code = int(state_code)
        except Exception:
            return 500, msg
        return state_code, msg

    def parseAddr(self, msg):
        '''Find ip and port in message'''
        matches = re.findall(r'\d+,\d+,\d+,\d+,\d+,\d+', msg)
        if len(matches) != 0:
            return matches[0]
        else: 
            return ''

    def isValidCommand(self, comamd):
        '''Check if command is supported'''
        for cmd in self.valid_cmd_set:
            if cmd == comamd:
                return True
        return False

    def msgProc(self, raw_input):
        '''Client main message process'''
        '''Input command and return reponse and error info parsed'''
        user_input = raw_input.strip()
        out_msg = ''
        command, param = self.parseInput(user_input)
        if not self.isValidCommand(command):
            out_msg += '# Error: Command not found\n'
            return out_msg
        if command == 'STOR':
            param_new = param.split('/')[-1]
            user_input = command + ' ' + param_new
        user_input += '\r\n'

        if command != 'RETR' and command != 'STOR' and command != 'LIST':
            # File transfer command receive messages twice from the server
            try:
                self.cli_sock.send(bytes(user_input, encoding='utf8'))
            except Exception:
                out_msg += '# Error: The connection has broken\n'
                self.connect_sock.close()
                if self.transfer_mode == 'port':
                    self.listen_sock.close()
                self.transfer_mode = ''
                return out_msg
            raw_response = self.cli_sock.recv(self.BUFSIZE)
            response = str(raw_response, encoding='utf8')
            out_msg += '< '
            out_msg += response
            state_code, msg = self.parseResponse(response)
        else:
            if self.transfer_mode == '':
                out_msg += '# Error: Use PASV/PORT first\n'
                return out_msg
            elif command == 'STOR':
                try:
                    open(param, 'rb')
                except Exception:
                    out_msg += '# Error: File not found\n'
                    return out_msg
                else:
                    self.cli_sock.send(bytes(user_input, encoding='utf8'))
            else: 
                self.cli_sock.send(bytes(user_input, encoding='utf8'))
        if command == 'QUIT' or command == 'ABOR':
            self.cli_sock.close()
            return out_msg
        elif command == 'PASV':         
            try:
                addr_info = self.parseAddr(msg).split(',')
                self.file_ip = '.'.join(addr_info[:4])
                self.file_port = 256 * int(addr_info[4]) + int(addr_info[5])
                self.transfer_mode = 'pasv'
            except Exception:
                out_msg += '# Error: Response format error\n'
        elif command == 'PORT':
            try:
                addr_info = param.split(',')
                self.listen_ip = '.'.join(addr_info[:4])
                self.listen_port = 256 * int(addr_info[4]) + int(addr_info[5])
            except Exception:
                out_msg += '# Error: Param format error\n'
            else:
                # start listening
                self.listen_sock = socket(AF_INET, SOCK_STREAM)
                try:
                    self.listen_sock.bind((self.listen_ip, self.listen_port))
                except Exception:
                    out_msg += '# Error: Socket bind error\n'
                else:
                    self.listen_sock.listen()
                    self.transfer_mode = 'port'
        elif command == 'RETR':
            # start connection
            if self.transfer_mode == 'pasv':
                self.connect_sock = socket(AF_INET, SOCK_STREAM)
                try:
                    self.connect_sock.connect((self.file_ip, self.file_port))
                except Exception:
                    out_msg += '# Error: Connection refused\n'
                    return out_msg
            elif self.transfer_mode == 'port':
                self.connect_sock, addr = self.listen_sock.accept()
            
            raw_response = self.cli_sock.recv(self.BUFSIZE)
            response = str(raw_response, encoding='utf8')
            matches = re.findall(r'(\d+) byte', response)
            if len(matches) != 0:
                self.filesize = int(matches[0])
            out_msg += '< ' 
            out_msg += response
            state_code, msg = self.parseResponse(response)
            if state_code == 150:
                try:
                    with open(param, 'wb') as f:
                        while True:
                            buf_read = self.connect_sock.recv(self.BUFSIZE)
                            write_n = f.write(buf_read)
                            self.total_write += write_n
                            if write_n == 0:
                                break
                except Exception:
                    out_msg += '# Error: The connection has broken\n'
                    return out_msg
            else:
                out_msg += '# Error: Transfer failed\n'

            self.connect_sock.close()
            if self.transfer_mode == 'port':
                self.listen_sock.close()
            self.transfer_mode = ''

            if state_code == 150:
                raw_response = self.cli_sock.recv(self.BUFSIZE)
                response = str(raw_response, encoding='utf8')
                self.total_write = 0
                self.filesize = 0
                out_msg += '< ' 
                out_msg += response
        elif command == 'STOR':
            if self.transfer_mode == 'pasv':
                self.connect_sock = socket(AF_INET, SOCK_STREAM)
                try:
                    self.connect_sock.connect((self.file_ip, self.file_port))
                except Exception:
                    out_msg += '# Error: Connection refused\n'
                    return out_msg
            elif self.transfer_mode == 'port':
                self.connect_sock, addr = self.listen_sock.accept()
            raw_response = self.cli_sock.recv(self.BUFSIZE)
            response = str(raw_response, encoding='utf8')
            out_msg += '< ' 
            out_msg += response
            state_code, msg = self.parseResponse(response)
            if state_code == 150:
                try:
                    with open(param, 'rb') as f:
                        while True:
                            buf_read = f.read(self.BUFSIZE)
                            send_n = self.connect_sock.send(buf_read)
                            if send_n == 0:
                                break
                except Exception:
                    out_msg += '# Error: The connection has broken\n'
                    self.connect_sock.close()
                    if self.transfer_mode == 'port':
                        self.listen_sock.close()
                    self.transfer_mode = ''
                    return out_msg
            else:
                out_msg += '# Error: Transfer failed\n'

            self.connect_sock.close()
            if self.transfer_mode == 'port':
                self.listen_sock.close()
            self.transfer_mode = ''

            if state_code == 150:
                raw_response = self.cli_sock.recv(self.BUFSIZE)
                response = str(raw_response, encoding='utf8')
                out_msg += '< '
                out_msg += response
        elif command == 'LIST':
            if self.transfer_mode == 'pasv':
                self.connect_sock = socket(AF_INET, SOCK_STREAM)
                try:
                    self.connect_sock.connect((self.file_ip, self.file_port))
                except Exception:
                    out_msg += '# Error: Connection refused\n'
                    return out_msg
            elif self.transfer_mode == 'port':
                self.connect_sock, addr = self.listen_sock.accept()

            raw_response = self.cli_sock.recv(self.BUFSIZE)
            response = str(raw_response, encoding='utf8')
            out_msg += '< ' 
            out_msg += response
            state_code, msg = self.parseResponse(response)
            if state_code == 150:
                raw_response = self.connect_sock.recv(self.BUFSIZE)
                response = str(raw_response, encoding='utf8')
                out_msg += '< ' 
                out_msg += response
                raw_response = self.cli_sock.recv(self.BUFSIZE)
                response = str(raw_response, encoding='utf8')
                out_msg += '< ' 
                out_msg += response
            else:
                out_msg += '# Error: Transfer failed\n'

            self.connect_sock.close()
            if self.transfer_mode == 'port':
                self.listen_sock.close()
            self.transfer_mode = ''
        elif command == 'PASS':
            if state_code == 530:
                out_msg += '# Error: Please relogin with USER first\n'

        return out_msg
