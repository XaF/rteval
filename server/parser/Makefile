
CFLAGS  = -g -fPIC -I. -Wall -Werror $(shell pkg-config libxml-2.0 --cflags) $(shell pkg-config libxslt --cflags)
LDFLAGS = -lrt -lpthread -lpq $(shell pkg-config libxml-2.0 --libs) $(shell pkg-config libxslt --libs)

OBJS = argparser.o configparser.o eurephia_nullsafe.o \
	eurephia_values.o eurephia_xml.o log.o parsethread.o pgsql.o sha1.o \
	xmlparser.o rteval_parserd.o

rteval_parserd : $(OBJS)
	gcc -g -o $@ $^ $(LDFLAGS)

clean :
	rm -f $(OBJS) rteval_parserd *~
