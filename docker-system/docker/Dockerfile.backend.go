# ---- build stage ----
FROM golang:1.23.5 AS build
WORKDIR /src
COPY agenthub_go/go.mod agenthub_go/go.sum ./
RUN go mod download
COPY agenthub_go/ .
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/agenthub ./cmd/agenthub
# The server creates its data directories at startup; distroless has no shell, so prepare them here
RUN mkdir -p /out/data/logs /out/data/rules /out/data/resources

# ---- runtime stage ----
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/agenthub /agenthub
COPY --from=build --chown=65532:65532 /out/data /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD ["/agenthub","-healthcheck"]
ENTRYPOINT ["/agenthub"]
