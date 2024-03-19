FROM alpine:3.19.1 as protoserv



# Metadata
LABEL maintainer="Artur Zdolinski <artur@nchekwa.com>" \
  org.label-schema.name=${BUILD_NAME} \
  org.label-schema.version=${BUILD_VERSION} \
  org.label-schema.description="Apstra Protoserv" \
  org.label-schema.license="AGPL-3.0" \
  org.label-schema.url="https://gitlab.com/nchekwa/apstra-protoserv/blob/master/README.md" \
  org.label-schema.build-date=${BUILD_DATE} \
  org.label-schema.vcs-url="https://gitlab.com/nchekwa/apstra-protoserv" \
  org.label-schema.docker.dockerfile="/Dockerfile" \
  org.label-schema.schema-version=${VERSION}


# Install
WORKDIR /tmp

RUN apk --update --no-cache add \
        py3-websockets py3-protobuf tini protoc



#################################################
RUN adduser -D -u 1001 -G root protoserv && \
    mkdir -p /opt/protoserv && \
    mkdir -p /opt/protoserv/proto && \
    mkdir -p /opt/protoserv/protoserv && \
    chown -R protoserv:0 /opt/protoserv

WORKDIR /opt/protoserv/

COPY server.py /opt/protoserv/
COPY ./proto /opt/protoserv/proto/
COPY ./protoserv /opt/protoserv/protoserv/
RUN chown -R protoserv:0 /opt/protoserv


# Tune bash command
RUN echo 'alias ll="ls -l"' >> ~/.bashrc && \
    echo 'alias la="ls -la"' >> ~/.bashrc


EXPOSE 4444/tcp 8765/tcp
WORKDIR /opt/protoserv
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/opt/protoserv/server.py"]

