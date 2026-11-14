CC = cc
.PHONY: all clean test
all: app
app: main.o
	$(CC) main.o -o app
main.o: main.c unused.h
	$(CC) -c main.c -o main.o
test: app
	./app
clean:
	rm -f app main.o
