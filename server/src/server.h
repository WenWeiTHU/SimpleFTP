/* server.h */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <ctype.h>
#include <string.h>
#include <linux/limits.h>
#include <sys/types.h>  
#include <sys/stat.h> 
#include <netdb.h>
#include <time.h>
#include <dirent.h>
#include "wrap.h"


#ifndef SERVER_H
#define SERVER_H

// Some constraints
#define DEFAULT_PORT 21
#define DEFAULT_ROOT "/tmp"
#define DEFAULT_SYST "L8"

#define BUFSIZE 4096
#define MAXLEN_RESPONSE 5000
#define MAX_CLIENT_WAIT 100

// Definition of Response
#define WELCOME "220 Anonymous FTP server ready.\r\n"
#define INVALID_CMD "500 Invalid command.\r\n"
#define VALID_USER "331 Guest login ok, send your complete e-mail address as password.\r\n"
#define INVALID_USER "530 Invalid user name.\r\n"
#define SHOULD_LOGIN "503 Please login first.\r\n"
#define SHOULD_FOLLOW "503 User-PASS or RNFR-RNTO should follow.\r\n"
#define LOGGING_OK "230 Guest login ok, access restrictions apply.\r\n"
#define PASSWD_FAIL "530 Authentication failed.\r\n"
#define SYST_INFO "215 UNIX Type: L8\r\n"
#define SET_TYPE_I "200 Type set to I.\r\n"
#define SET_TYPE_ERROR "502 Type not supported.\r\n"
#define USER_QUIT "221 Goodbye.\r\n"
#define CUR_DIR "257 \"%s\"\r\n"
#define PORT_OK "200 PORT command successful.\r\n"
#define PORT_FAIL "501 PORT command fail.\r\n"
#define PASV_OK "227 Entering Passive Mode(%s)\r\n"
#define CONNECT_FAIL "425 Connection attempt fail.\r\n"
#define CONNECT_OK "150 Opening BINARY mode data connection for %s.\r\n"
#define CONNECT_OK_LIST "150 Opening BINARY mode data connection for directory inforamtion.\r\n"
#define CONNECT_OK_RETR "150 Opening BINARY mode data connection for %s (%d bytes).\r\n"
#define FILE_FAIL "451 File open fail.\r\n"
#define READ_DIR_FAIL "451 Read directory fail.\r\n"
#define FILE_OVER "226 Transfer complete.\r\n"
#define PERMISSION_DENY "550 Permission deny.\r\n"
#define DIR_NOT_FOUND "550 %s: No such file or directory.\r\n"
#define DIR_OK "250 Directory change okay.\r\n"
#define MAKE_DIR_OK "250 Directory create successfully.\r\n"
#define MAKE_DIR_FAIL "550 Directory create fail.\r\n"
#define RM_DIR_OK "250 Directory remove successfully.\r\n"
#define RM_DIR_FAIL "550 Directory remove fail.\r\n"
#define PORT_PASV_NEEDED "503 PORT/PASV needed.\r\n"
#define RNFR_OK "350 OK File exist.\r\n"
#define RNFR_FAIL "550 File not found.\r\n"
#define RNTO_OK "250 File rename successfully.\r\n"
#define RNTO_FAIL "550 File rename fail.\r\n"
#define REST_OK "350 Restart position accepted (%d).\r\n"


// Definition of Commands
#define USER "USER"
#define PASS "PASS"
#define RETR "RETR"
#define STOR "STOR"
#define QUIT "QUIT"
#define SYST "SYST"
#define TYPE "TYPE"
#define PORT "PORT"
#define PASV "PASV"
#define MKD  "MKD"
#define CWD  "CWD"
#define PWD  "PWD"
#define LIST "LIST"
#define RMD  "RMD"
#define RNFR "RNFR"
#define RNTO "RNTO"
#define REST "REST"
#define ABOR "ABOR"

// Client's state
enum State {
    client_begin,    // before logging
    client_logging,  // be logging, when user got but password
    client_logged,   // be logged
    client_transfer, // after port/pasv received
    client_rename      // begin rename a file
};

enum Mode {
    mode_pasv, 
    mode_port
};

int getRandomPort();
int getLocalIP(char *ip);
void addSlashLeft(char* s);
void parentDir(char* path);
int startTCPListen(int port);
int getFileSize(char* filename);
int isValidCmd(char* command_raw);
int isRelDirExist(char* rel_path);
int isValidUser(char* command_raw);
int isValidPasswd(char* command_raw);
int listDir(char* path, char* param);
int startTCPConnect(char* ip, int port);
int Rename(char* oldname, char* newname);
int makeDir(char* cur_path, char* new_dir);
int removeDir(char* cur_path, char* new_dir);
void packAddrPort(char* param, char* ip, int port);
int parseAddrPort(char* param, char* ip, int* port);
void parseArgs(int argc, char** argv, int *port, char* root);


#endif
