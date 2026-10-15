// Command agenthub serves the Go port of the 4genthub backend.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/utilities"
)

func main() {
	utilities.LoadDefaultEnv()

	healthcheckFlag := flag.Bool("healthcheck", false, "check the health endpoint and exit")
	flag.Parse()

	port := envOr("FASTMCP_PORT", "8000")

	if *healthcheckFlag {
		if err := healthcheck(port); err != nil {
			log.Printf("healthcheck failed: %v", err)
			os.Exit(1)
		}
		return
	}

	ctx := context.Background()
	// models.py registers the timestamp events at import time.
	database.SetupTimestampEvents()
	deps := database.OSDeps()
	if err := database.InitDatabase(ctx, deps); err != nil {
		log.Fatalf("database init: %v", err)
	}
	cfg, err := database.GetInstance(ctx, deps)
	if err != nil {
		log.Fatalf("database config: %v", err)
	}
	sessions := database.NewSessionManager(cfg)
	app, err := httpapp.NewApp(ctx, sessions)
	if err != nil {
		log.Fatalf("app: %v", err)
	}

	// The task lifecycle sweep: one pass per TASK_SWEEP_INTERVAL (default 1h) over the tasks the
	// owner's ruling covers, started here under sigCtx and guarded by a Postgres advisory lock so
	// two server instances never sweep twice. Composed BEFORE the server starts on purpose: the
	// schedule is read from the environment here, and a malformed TASK_* variable fails startup
	// rather than being quietly served the default a misspelling was meant to replace.
	sweeper, err := httpapp.NewTaskLifecycleSweeper(ctx, sessions)
	if err != nil {
		log.Fatalf("task lifecycle sweeper: %v", err)
	}

	host := envOr("FASTMCP_HOST", "0.0.0.0")
	srv := &http.Server{
		Addr:              host + ":" + port,
		Handler:           app.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       60 * time.Second,
		WriteTimeout:      0, // SSE /mcp must be able to stream indefinitely.
		IdleTimeout:       120 * time.Second,
	}

	sigCtx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	go sweeper.Run(sigCtx)

	serverErr := make(chan error, 1)
	go func() {
		log.Printf("agenthub listening on %s:%s", host, port)
		serverErr <- srv.ListenAndServe()
	}()

	select {
	case err := <-serverErr:
		if err != nil && err != http.ErrServerClosed {
			log.Fatalf("server: %v", err)
		}
	case <-sigCtx.Done():
		stop()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			log.Fatalf("server shutdown: %v", err)
		}
		log.Printf("agenthub shutdown complete")
	}
}

// healthcheck reports whether the local server's /health endpoint returns 200.
func healthcheck(port string) error {
	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://127.0.0.1:" + port + "/health")
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("healthcheck: unexpected status %d", resp.StatusCode)
	}
	return nil
}

func envOr(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}
