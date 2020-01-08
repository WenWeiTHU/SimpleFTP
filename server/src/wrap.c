/* wrap.c */
/* this file wrapped some commom socket api with error handling */
#include "wrap.h"


int Accept(int fd, struct sockaddr *sa, socklen_t *salenptr)
{
	int n;

	while(1){
		n = accept(fd, sa, salenptr);
		if(n >= 0){
			break;
		} else if ((errno == ECONNABORTED) || (errno == EINTR)){
			continue;
		} else {
			perror("accept error");
			break;
		}
	}
	return n;
}

void Bind(int fd, const struct sockaddr *sa, socklen_t salen)
{
	if (bind(fd, sa, salen) < 0){
		perror("bind error");
	}	
}

void Connect(int fd, const struct sockaddr *sa, socklen_t salen)
{
	if (connect(fd, sa, salen) < 0){
		perror("connect error");
	}	
}

void Listen(int fd, int backlog)
{
	if (listen(fd, backlog) < 0){
		perror("listen error");
	}	
}

int Socket(int family, int type, int protocol)
{
	int n;

	if ((n = socket(family, type, protocol)) < 0) {
		perror("socket error");
	}
		
	return n;
}

ssize_t Read(int fd, void *ptr, size_t nbytes)
{
	ssize_t n;

	while(1){
		n = read(fd, ptr, nbytes);
		if(n != -1){
			break;
		} else if (errno == EINTR) {
			continue;
		} else {
			return -1;
		}
	}
	return n;
}

ssize_t Write(int fd, const void *ptr, size_t nbytes)
{
	ssize_t n;

	while(1){
		n = write(fd, ptr, nbytes);
		if(n != -1){
			break;
		} else if(errno == EINTR) {
			continue;
		} else {
			return -1;
		}
	}

	return n;
}

void Close(int fd)
{
	if (close(fd) == -1){
		perror("close error");
	}
}
