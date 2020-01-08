/* server.c */
#include "server.h"


int port;              // listen port
char root[PATH_MAX];   // max rel path limit
char cur_root[PATH_MAX];

int main(int argc, char **argv)
{  
	socklen_t cliaddr_len;
	int listenfd, connfd, connfd_file, listenfd_file;
    struct sockaddr_in cliaddr, cliaddr_file;
	char buf[BUFSIZE], response[MAXLEN_RESPONSE];
    char command[5], param[PATH_MAX], file_path[PATH_MAX];
    char file_ip[25];
    int transfer_mode;
    int file_port;
	int buf_read;
    int read_len;
    FILE *fp;

    // get port and root
    parseArgs(argc, argv, &port, root);
    if(!isRelDirExist(root)){
        perror("root not exists");
        exit(1);
    }

    strcpy(cur_root, root);             // initialize cur_root
    listenfd = startTCPListen(port);    // start listening for client
	
    while (1) {
		cliaddr_len = sizeof(cliaddr);
		connfd = Accept(listenfd, (struct sockaddr *)&cliaddr, &cliaddr_len);
        connfd_file = -1;  // -1 means the file descriptor not used or has been closed
        listenfd_file = -1;
        transfer_mode = mode_pasv;
		
        // use muti-process to deal with multiple clients
		int pid = fork();
		if(pid == -1){
            // start new process failed
			perror("call to fork failed");
			exit(1);
		} else if (pid == 0) {
            // in new child process deal with each client's connection
            // listen socket should be closed
			Close(listenfd);
            listenfd = -1;
            int restSize = 0;
            Write(connfd, WELCOME, strlen(WELCOME)); // send welcome msg
            enum State state = client_begin;         // init client state
            enum State state_tmp = client_begin;     // use to recover state if get RNFR 

			while (1) {
                memset(buf, 0, sizeof(buf));
                memset(param, 0, sizeof(param));
                // message loop to get command from client
				buf_read = Read(connfd, buf, BUFSIZE);
				if (buf_read == 0) {
					// printf("the other side has been closed.\n");
					break;
				}

                if(isValidCmd(buf) == 0){
                    // printf("invalid command\n");
                    // send command error msg
                    Write(connfd, INVALID_CMD, strlen(INVALID_CMD));
                    continue;
                }

                sscanf(buf, "%s %s", command, param);

                for(unsigned int k = 0; k < strlen(command); k++){
                    command[k] = toupper(command[k]);
                }
                // printf("command: %s\nparam: %s\n", command, param);

                switch (state){        // jump by user state
                    case client_begin: // before sending USER
                        if(strcmp(command, USER) == 0){
                            if(isValidUser(param)){
                                Write(connfd, VALID_USER, strlen(VALID_USER));
                                state = client_logging;
                            } else {
                                Write(connfd, INVALID_USER, strlen(INVALID_USER));
                            }
                        } else {
                            Write(connfd, SHOULD_LOGIN, strlen(SHOULD_LOGIN));
                        }
                        break;
                    case client_logging:
                        if(strcmp(command, PASS) == 0){
                            if(isValidPasswd(param)){
                                Write(connfd, LOGGING_OK, strlen(LOGGING_OK));
                                state = client_logged;
                            } else {
                                Write(connfd, PASSWD_FAIL, strlen(PASSWD_FAIL));
                            }
                        } else if(strcmp(command, USER) == 0){
                            if(isValidUser(param)){
                                Write(connfd, VALID_USER, strlen(VALID_USER));
                                state = client_logging;
                            } else {
                                Write(connfd, INVALID_USER, strlen(INVALID_USER));
                                state = client_begin;
                            }
                        } else {
                            Write(connfd, SHOULD_FOLLOW, strlen(SHOULD_FOLLOW));
                        }
                        break;
                    case client_transfer:
                        if(strcmp(command, RETR) == 0){
                            // 1.get file path
                            strcpy(file_path, cur_root);
                            addSlashLeft(param);
                            strcat(file_path, param);

                            // 2.try to open file
                            fp = fopen(file_path, "rb");
                            if(!fp){
                                Write(connfd, FILE_FAIL, strlen(FILE_FAIL));
                                if(transfer_mode == mode_pasv && listenfd_file != -1){
                                    Close(listenfd_file);
                                    listenfd_file = -1;
                                }
                                break;
                            }

                            // 3.start connection or accepting
                            if(transfer_mode == mode_pasv){
                                socklen_t cliaddr_file_len = sizeof(cliaddr_file);
                                connfd_file = Accept(listenfd_file, (struct sockaddr *)&cliaddr_file, &cliaddr_file_len);
                            } else if (transfer_mode == mode_port){
                                connfd_file = startTCPConnect(file_ip, file_port);
                            }
                            if(connfd_file == -1){
                                Write(connfd, CONNECT_FAIL, strlen(CONNECT_FAIL));
                                break;
                            } else{
                                sprintf(response, CONNECT_OK_RETR, file_path, getFileSize(file_path));
                                Write(connfd, response, strlen(response));
                            }
                            fseek(fp, restSize, SEEK_SET);

                            // 4.send file
                            while(1){
                                read_len = fread(response, sizeof(char), BUFSIZE, fp);
                                Write(connfd_file, response, read_len);
                                if(read_len == 0){
                                    break;
                                }
                            }
                            fclose(fp);
                            Write(connfd, FILE_OVER, strlen(FILE_OVER));
                            restSize = 0;

                            // 5.close connection established before
                            if(connfd_file != -1){
                                Close(connfd_file);
                                connfd_file = -1;
                            }
                            if(transfer_mode == mode_pasv && listenfd_file != -1){
                                Close(listenfd_file);
                                listenfd_file = -1;
                            }
                            state = client_logged;
                            break;
                        } else if(strcmp(command, STOR) == 0){
                            strcpy(file_path, cur_root);
                            addSlashLeft(param);
                            strcat(file_path, param);

                            umask(0000);
                            fp = fopen(file_path, "wb+");
                            if(!fp){
                                Write(connfd, FILE_FAIL, strlen(FILE_FAIL));
                                if(transfer_mode == mode_pasv && listenfd_file != -1){
                                        Close(listenfd_file);
                                        listenfd_file = -1;
                                }
                                break;
                            }

                            if(transfer_mode == mode_pasv){
                                socklen_t cliaddr_file_len = sizeof(cliaddr_file);
                                connfd_file = Accept(listenfd_file, (struct sockaddr *)&cliaddr_file, &cliaddr_file_len);
                            } else if (transfer_mode == mode_port){
                                connfd_file = startTCPConnect(file_ip, file_port);  
                            }
                            if(connfd_file == -1){
                                Write(connfd, CONNECT_FAIL, strlen(CONNECT_FAIL));
                                break;
                            } else {
                                sprintf(response, CONNECT_OK, param);
                                Write(connfd, response, strlen(response));
                            }

                            while(1){
                                read_len = Read(connfd_file, response, BUFSIZE);
                                fwrite(response, sizeof(char), read_len, fp);
                                if(read_len == 0){
                                    break;
                                }
                            }
                            fclose(fp);
                            Write(connfd, FILE_OVER, strlen(FILE_OVER));

                            if(connfd_file != -1){
                                Close(connfd_file);
                                connfd_file = -1;
                            }
                            if(transfer_mode == mode_pasv && listenfd_file != -1){
                                Close(listenfd_file);
                                listenfd_file = -1;
                            }
                            state = client_logged;
                            break;
                        } else if(strcmp(command, LIST) == 0){
                            // like RETR, add a step to save dir info into a file, then send the file, finally remove it
                            if(listDir(cur_root, param) == -1){
                                Write(connfd, READ_DIR_FAIL, strlen(READ_DIR_FAIL));
                                if(transfer_mode == mode_pasv && listenfd_file != -1){
                                    Close(listenfd_file);
                                    listenfd_file = -1;
                                }
                                break;
                            }

                            fp = fopen(".dir_info.txt", "rb"); // store dir information in this file and send this file
                            if(!fp){
                                Write(connfd, READ_DIR_FAIL, strlen(READ_DIR_FAIL));
                                if(transfer_mode == mode_pasv && listenfd_file != -1){
                                    Close(listenfd_file);
                                    listenfd_file = -1;
                                }
                                break;
                            }

                            if(transfer_mode == mode_pasv){
                                socklen_t cliaddr_file_len = sizeof(cliaddr_file);
                                connfd_file = Accept(listenfd_file, (struct sockaddr *)&cliaddr_file, &cliaddr_file_len);
                            } else if (transfer_mode == mode_port){
                                connfd_file = startTCPConnect(file_ip, file_port);    
                            }
                            if(connfd_file == -1){
                                Write(connfd, CONNECT_FAIL, strlen(CONNECT_FAIL));
                                if(transfer_mode == mode_pasv && listenfd_file != -1){
                                    Close(listenfd_file);
                                    listenfd_file = -1;
                                }
                                remove(".dir_info.txt");
                                break;
                            } else {
                                sprintf(response, CONNECT_OK_LIST);
                                Write(connfd, response, strlen(response));
                            }

                            while(1){
                                read_len = fread(response, sizeof(char), BUFSIZE, fp);
                                Write(connfd_file, response, read_len);
                                if(read_len == 0){
                                    break;
                                }
                            }
                            fclose(fp);
                            Write(connfd, FILE_OVER, strlen(FILE_OVER));
                            remove(".dir_info.txt");

                            if(connfd_file != -1){
                                Close(connfd_file);
                                connfd_file = -1;
                            }
                            if(transfer_mode == mode_pasv && listenfd_file != -1){
                                Close(listenfd_file);
                                listenfd_file = -1;
                            }
                            state = client_logged;
                            break;
                        } else if(strcmp(command, REST) == 0){
                            restSize = atoi(param);
                            sprintf(response, REST_OK, restSize);
                            Write(connfd, response, strlen(response));
                            break;
                        }
                    case client_logged:
                        if(strcmp(command, SYST) == 0){
                            Write(connfd, SYST_INFO, strlen(SYST_INFO));
                        } else if(strcmp(command, TYPE) == 0){
                            if (strcmp(param, "I") == 0 || strcmp(param, "A") == 0) {
                                // only binary mode is supported
                                // ascii mode is seen as binary mode
                                Write(connfd, SET_TYPE_I, strlen(SET_TYPE_I));
                            } else {
                                Write(connfd, SET_TYPE_ERROR, strlen(SET_TYPE_ERROR));
                            }
                        } else if(strcmp(command, QUIT) == 0 || strcmp(command, ABOR) == 0){
                            Write(connfd, USER_QUIT, strlen(USER_QUIT));
                            Close(connfd);
                            if(connfd_file != -1){
                                Close(connfd_file);
                                connfd_file = -1;
                            }
                            if(listenfd_file != -1){
                                Close(listenfd_file);
                                listenfd_file = -1;
                            }
                            // printf("Client at [PORT] %d closed connection\n", port);
                            exit(0);
                        } else if(strcmp(command, PORT) == 0){                         
                            if(parseAddrPort(param, file_ip, &file_port)){
                                if(connfd_file != -1){
                                    Close(connfd_file);
                                    connfd_file = -1;
                                }
                                if(listenfd_file != -1){
                                    Close(listenfd_file);
                                    listenfd_file = -1;
                                }
                                Write(connfd, PORT_OK, strlen(PORT_OK));
                                state = client_transfer;
                                transfer_mode = mode_port;
                            } else {
                                Write(connfd, PORT_FAIL, strlen(PORT_FAIL));
                            }      
                        } else if(strcmp(command, PASV) == 0){
                            if(connfd_file != -1){
                                Close(connfd_file);
                                connfd_file = -1;
                            }
                            if(listenfd_file != -1){
                                Close(listenfd_file);
                                listenfd_file = -1;
                            }
                            file_port = getRandomPort();
                            getLocalIP(file_ip);
                            packAddrPort(param, file_ip, file_port);
                            sprintf(response, PASV_OK, param);
                            state = client_transfer;
                            transfer_mode = mode_pasv;                    
                            Write(connfd, response, strlen(response));   
                            // start listening
                            listenfd_file = startTCPListen(file_port);
                        } else if(strcmp(command, RETR) == 0 || strcmp(command, STOR) == 0 || strcmp(command, LIST) == 0){
                            Write(connfd, PORT_PASV_NEEDED, strlen(PORT_PASV_NEEDED)); 
                        } else if(strcmp(command, MKD) == 0){
                            // all the dir-releted command is change the string: cur_root, not change the working directory
                            if(makeDir(cur_root, param)){
                                Write(connfd, MAKE_DIR_OK, strlen(MAKE_DIR_OK));
                            } else {
                                Write(connfd, MAKE_DIR_FAIL, strlen(MAKE_DIR_FAIL));
                            }
                        } else if(strcmp(command, CWD) == 0){
                            if(strcmp(param, ".") == 0 || strcmp(param, "./") == 0 || strcmp(param, "/.") == 0){
                                Write(connfd, DIR_OK, strlen(DIR_OK));
                            } else if(strcmp(param, "..") == 0 || strcmp(param, "../") == 0 || strcmp(param, "/..") == 0){
                                if(strcmp(cur_root, root) != 0){
                                    parentDir(cur_root);
                                    Write(connfd, DIR_OK, strlen(DIR_OK));
                                } else {
                                    Write(connfd, PERMISSION_DENY, strlen(PERMISSION_DENY));
                                }
                            } else {
                                char tmp_root[PATH_MAX];
                                parentDir(param); // remove the last '/'
                                strcpy(tmp_root, cur_root);
                                if(param[0] == '/'){
                                    strcpy(cur_root, root);
                                    strcat(cur_root, param);
                                } else {
                                    addSlashLeft(param);
                                    strcat(cur_root, param);
                                }                              
                                if(isRelDirExist(cur_root)){
                                    Write(connfd, DIR_OK, strlen(DIR_OK));
                                } else {
                                    strcpy(cur_root, tmp_root);
                                    sprintf(response, DIR_NOT_FOUND, param);
                                    Write(connfd, response, strlen(response));
                                }
                            }
                        } else if(strcmp(command, PWD) == 0){
                            sprintf(response, CUR_DIR, cur_root);
                            Write(connfd, response, strlen(response));
                        } else if(strcmp(command, RMD) == 0){
                            if(removeDir(cur_root, param)){
                                Write(connfd, RM_DIR_OK, strlen(RM_DIR_OK));
                            } else {
                                Write(connfd, RM_DIR_FAIL, strlen(RM_DIR_FAIL));
                            }
                        } else if(strcmp(command, RNFR) == 0){
                            addSlashLeft(param);
                            strcat(cur_root, param);

                            if(isRelDirExist(cur_root)){
                                Write(connfd, RNFR_OK, strlen(RNFR_OK));
                                state_tmp = state;
                                state = client_rename;
                            } else {   
                                Write(connfd, RNFR_FAIL, strlen(RNFR_FAIL));
                                parentDir(cur_root);
                            }
                        } else if(strcmp(command, RNTO) == 0){
                            Write(connfd, SHOULD_FOLLOW, strlen(SHOULD_FOLLOW));
                        } else if(strcmp(command, REST) == 0){
                            restSize = atoi(param);
                            sprintf(response, REST_OK, restSize);
                            Write(connfd, response, strlen(response));
                        }
                        break;
                    case client_rename:
                        state = state_tmp;
                        if(strcmp(command, RNTO) == 0){                         
                            if(Rename(cur_root, param) == 0){
                                Write(connfd, RNTO_OK, strlen(RNTO_OK));
                            } else {
                                Write(connfd, RNTO_FAIL, strlen(RNTO_FAIL));
                            }
                        } else{
                            Write(connfd, SHOULD_FOLLOW, strlen(SHOULD_FOLLOW));
                        }
                        parentDir(cur_root);
                        break;
                    default:
                        break;
                }
			}
            // child process should exit when client quit
			Close(connfd);
			exit(0);
		} else
            // in parent process continue listening
            // connection socket should be closed
			Close(connfd);
	}

    return 0;
}

void parseArgs(int argc, char** argv, int *port, char* root) {
    // get port and root from sys arg

    int i;
    *port = DEFAULT_PORT;
    strcpy(root, DEFAULT_ROOT);
    for (i = 0; i < argc; i++) {
        if (strcmp(argv[i], "-port") == 0) {
            if (i + 1 < argc)
                sscanf(argv[i+1], "%d", port);
        } else if (strcmp(argv[i], "-root") == 0) {
            if (i + 1 < argc) 
                strcpy(root, argv[i+1]);
        }
    }
}

int isValidCmd(char* command_raw) {
    // check if valid command and  print the command and port received
    // return 1 if the command is valid, 0 otherwise
    
    int i;
    int end;
    char command[5];
    int len_command = strlen(command_raw);
    char* valid_command_set[] = {USER, PASS, RETR, STOR, QUIT, SYST, TYPE, PORT, PASV,
    MKD, CWD, PWD, LIST, RMD, RNFR, RNTO, ABOR, REST};

    for (end = 0; end < len_command; end++){
        if (command_raw[end] == ' ' || command_raw[end] == '\r' || command_raw[end] == '\n') break;
    }
    end--;
    if(command_raw[end] != ' ') end++;
    for (i = 0; i < end; i++)
        command[i] = toupper(command_raw[i]);
    command[end] = '\0';

    for(i = 0; i < 18; i++){
        if (strcmp(command, valid_command_set[i]) == 0){
            return 1;
        }
    }
    return 0;
}

int isValidUser(char* username){
    // check username
    // only accept 'anonymous'

    return strcmp(username, "anonymous") == 0;
}

int isValidPasswd(char* username){
    // check password
    // accept everything

    return 1;
}

int parseAddrPort(char* param, char* ip, int* port){
    // from parameter sent by PORT extract ip and port
    int h1 = -1;
    int h2 = -1; 
    int h3 = -1;
    int h4 = -1;
    int p1 = -1;
    int p2 = -1;

    sscanf(param, "%d,%d,%d,%d,%d,%d", &h1, &h2, &h3, &h4, &p1, &p2);
    if(h1 == -1 || h2 == -1 || h3 == -1 ||
       h4 == -1 || p1 == -1 || p2 == -1 ){
           return 0;
       }
    sprintf(ip, "%d.%d.%d.%d", h1, h2, h3, h4);
    *port = 256 * p1 + p2;

    return 1;
}

void packAddrPort(char* param, char* ip, int port){
    // pack ip and port to a command sent by PASV
    int p1 = port / 256;
    int p2 = port % 256;
    int h1, h2, h3, h4;

    sscanf(ip, "%d.%d.%d.%d", &h1, &h2, &h3, &h4);
    sprintf(param, "%d,%d,%d,%d,%d,%d", h1, h2, h3, h4, p1, p2);
}

int listDir(char* path, char* param){
    // use system command to get directory info
    char instr[MAXLEN_RESPONSE];
    char dir[PATH_MAX];
    struct stat s_buf;

    strcpy(dir, path);
    addSlashLeft(param);
    strcat(dir, param);

    stat(dir, &s_buf);
    if(S_ISREG(s_buf.st_mode)){
        sprintf(instr, "ls -l %s > .dir_info.txt", dir);
    } else if(S_ISDIR(s_buf.st_mode)){
        sprintf(instr, "ls %s -al | tail +4 > .dir_info.txt", dir);
    }

    return system(instr);
}

void parentDir(char* path){
    // remove the substr after the last '/'
    int len, i;

    len = strlen(path);
    for(i = len; i >= 0; i--){
        if(path[i] == '/'){
            path[i] = '\0';
            break;
        }
    }
}

int isRelDirExist(char* rel_path){
    // test the relative path existence
    if(access(rel_path, F_OK) == -1){
        return 0;
    } else {
        return 1;
    }
}

int makeDir(char* cur_path, char* new_dir){
    // make directory
    char tmp_path[BUFSIZE];

    strcpy(tmp_path, cur_path);

    if(new_dir[0] != '/'){
        strcat(tmp_path, "/");
    }
    strcat(tmp_path, new_dir);
    umask(0000);
    if(mkdir(tmp_path, S_IRWXU|S_IRWXG|S_IRWXO) == 0){
        return 1;
    } else {
        return 0;
    }
}

int removeDir(char* cur_path, char* new_dir){
    // remove derectory if empty
    char tmp_path[BUFSIZE];

    strcpy(tmp_path, cur_path);

    if(new_dir[0] != '/'){
        strcat(tmp_path, "/");
    }
    strcat(tmp_path, new_dir);
    if(rmdir(tmp_path) == 0){
        return 1;
    } else {
        return 0;
    }
}

int getRandomPort(){
    srand((unsigned)time(0));
    // get a random port between 20000 to 65535
    return rand() % 45535 + 20000;
}

int getLocalIP(char *ip) 
{
    // get local ip, 127.0.0.1 have a high priority
    int status = 0;
    int i = 0;
    char buf[128] = {0};
    char *local_ip = NULL;

    if (gethostname(buf, sizeof(buf)) == 0)
    {
        struct hostent *temp_he;
        temp_he = gethostbyname(buf);
        if (temp_he) 
        {
            for(i = 0; temp_he->h_addr_list[i]; i++)
            {
                local_ip = NULL;
                local_ip = inet_ntoa(*(struct in_addr *)(temp_he->h_addr_list[i]));
                if(local_ip)
                {
                    strcpy(ip, local_ip);
                    status = 1;
                }
            }
        }
    }

    return status;
}

int startTCPListen(int port){
    // start listening in a port
    struct sockaddr_in tcp_addr;
    int fd = Socket(AF_INET, SOCK_STREAM, 0);
	int opt = 1;
    // allow socket with the same port but different ip
	setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
	bzero(&tcp_addr, sizeof(tcp_addr));
	tcp_addr.sin_family = AF_INET;
	tcp_addr.sin_addr.s_addr = htonl(INADDR_ANY);
	tcp_addr.sin_port = htons(port);
    
    // original socket function is wrapped with Exception handling in wrap.c
	Bind(fd, (struct sockaddr *)&tcp_addr, sizeof(tcp_addr));
	Listen(fd, MAX_CLIENT_WAIT);
	// printf("Accepting connections at PORT [%d] ...\n", port);

    return fd;
}

int startTCPConnect(char* ip, int port){
    // connect specific ip and port
    struct sockaddr_in addr;
    int connfd;

    connfd = Socket(AF_INET, SOCK_STREAM, 0);
    bzero(&addr, sizeof(addr));
    addr.sin_family = AF_INET;
    inet_pton(AF_INET, ip, &addr.sin_addr);
    addr.sin_port = htons(port);
    if(connect(connfd, (struct sockaddr *)&addr, sizeof(addr)) < 0){
        perror("Connect error\n");
        return -1;
    }      

    return connfd;
}

int Rename(char* oldname, char* newname){
    // rename a file
    char new_file[PATH_MAX];

    strcpy(new_file, oldname);
    addSlashLeft(newname);
    parentDir(new_file);
    strcat(new_file, newname);

    // printf("%s\n%s\n", oldname, new_file);

    return rename(oldname, new_file);
}

void addSlashLeft(char* s){
    // add '/' in front of a string if s[0] is not '/'
    int idx = 0;
    if(s[0] != '/'){
        while(s[idx] != '\0'){
            idx++;
        }
        for( ; idx >= 0; idx--){
            s[idx+1] = s[idx];
        }
        s[0] = '/';
    }
}

int getFileSize(char* filename)
{
    struct stat statbuf;
    stat(filename, &statbuf);

    int size = statbuf.st_size;
 
    return size;
}
