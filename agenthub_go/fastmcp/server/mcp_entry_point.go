// Package server ports fastmcp/server/mcp_entry_point.py.
package server

import (
	"context"
	"log"
	"net/http"
	"os"

	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ServerConfig holds the server runtime options.
type ServerConfig struct {
	Host string
	Port string
}

// LoadServerConfig reads host and port from environment variables.
func LoadServerConfig() ServerConfig {
	host := os.Getenv("FASTMCP_HOST")
	if host == "" {
		host = "0.0.0.0"
	}
	port := os.Getenv("FASTMCP_PORT")
	if port == "" {
		port = "8000"
	}
	return ServerConfig{
		Host: host,
		Port: port,
	}
}

// SetupServer initializes the database, models, and returns a configured App.
func SetupServer(ctx context.Context) (*httpapp.App, error) {
	database.SetupTimestampEvents()
	deps := database.OSDeps()
	if err := database.InitDatabase(ctx, deps); err != nil {
		return nil, err
	}
	cfg, err := database.GetInstance(ctx, deps)
	if err != nil {
		return nil, err
	}
	sessions := database.NewSessionManager(cfg)
	return httpapp.NewApp(ctx, sessions)
}

// RunServer bootstraps and runs the HTTP server.
func RunServer(ctx context.Context) error {
	cfg := LoadServerConfig()
	app, err := SetupServer(ctx)
	if err != nil {
		log.Fatalf("server setup failed: %v", err)
		return err
	}
	addr := cfg.Host + ":" + cfg.Port
	log.Printf("agenthub listening on %s", addr)
	return http.ListenAndServe(addr, app.Handler())
}

type serverDiagnostics struct{}

func (serverDiagnostics) GetMCPStatus(reqID, sessionID string) any {
	ctx := NewContext(reqID, "", sessionID)
	return GetMCPStatus(ctx, false, nil, nil)
}

func (serverDiagnostics) SessionHealthCheck(reqID, sessionID string) any {
	ctx := NewContext(reqID, "", sessionID)
	return SessionHealthCheck(ctx)
}

func init() {
	httpapp.SetDiagnosticsProvider(serverDiagnostics{})
}
