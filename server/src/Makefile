server: server.o wrap.o 
	gcc -Wall -g server.o wrap.o -o server

server.o: server.c
	gcc -Wall -c -g server.c -o server.o
wrap.o: wrap.c
	gcc -Wall -c -g wrap.c -o wrap.o

.PHONY:clean
clean:
	rm -rf *.o 

