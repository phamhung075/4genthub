package services

// AuthContextService is the minimal surface DebugService needs from
// ContextImportService (Python import-probing module, not ported).
type AuthContextService interface {
	UserContextAvailable() bool
	GetCurrentUserID() *string
}

// DebugService mirrors debug_service.DebugService. All Python bodies only log, so
// the Go port keeps the calls that touch the context service and drops logging.
type DebugService struct {
	contextService AuthContextService
}

// NewDebugService mirrors DebugService(context_service).
func NewDebugService(contextService AuthContextService) *DebugService {
	return &DebugService{contextService: contextService}
}

// LogAuthenticationDetails mirrors log_authentication_details. The Python
// try/except Exception is mirrored with recover.
func (s *DebugService) LogAuthenticationDetails(userID *string, operation *string) {
	defer func() { _ = recover() }()

	if s.contextService != nil && s.contextService.UserContextAvailable() {
		s.contextService.GetCurrentUserID()
	}
}
