import { Folder, Menu, X } from 'lucide-react';
import { lazy, Suspense, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useParams, useNavigate } from 'react-router-dom';
import { Project } from './api';
import './App.css';
import './styles/animations.css';
import './styles/task-animations.css';
import './styles/subtask-animations.css';
import './styles/branch-animations.css';
import { Header } from './components/Header';
import { ShimmerButton } from './components/ui/shimmer-button';
import { ToastProvider } from './components/ui/toast';
import { ThemeProvider } from './contexts/ThemeContext';
// WebSocket is now handled in AuthContext, no need to import here
import { useAuth } from './contexts/AuthContext';

// Import WebSocket test utility for debugging
import './utils/testWebSocket';

// Lazy load heavy components for better code splitting
const AppLayout = lazy(() => import('./components/AppLayout').then(m => ({ default: m.AppLayout })));
const AuthWrapper = lazy(() => import('./components/auth').then(m => ({ default: m.AuthWrapper })));
const EmailVerification = lazy(() => import('./components/auth').then(m => ({ default: m.EmailVerification })));
const LoginForm = lazy(() => import('./components/auth').then(m => ({ default: m.LoginForm })));
const ProtectedRoute = lazy(() => import('./components/auth').then(m => ({ default: m.ProtectedRoute })));
const SignupForm = lazy(() => import('./components/auth').then(m => ({ default: m.SignupForm })));
const BranchDetailsDialog = lazy(() => import('./components/BranchDetailsDialog'));
const GlobalContextDialog = lazy(() => import('./components/GlobalContextDialog'));
const ProjectDetailsDialog = lazy(() => import('./components/ProjectDetailsDialog'));
const ProjectList = lazy(() => import('./components/ProjectList'));
const WebSocketStatusBadge = lazy(() => import('./components/WebSocketStatusBadge').then(m => ({ default: m.WebSocketStatusBadge })));
const LazyTaskList = lazy(() => import('./components/LazyTaskList'));

// Lazy load page components
const Profile = lazy(() => import('./pages/Profile').then(m => ({ default: m.Profile })));
const RegistrationSuccess = lazy(() => import('./pages/RegistrationSuccess'));
const TokenManagement = lazy(() => import('./pages/TokenManagement').then(m => ({ default: m.TokenManagement })));
const HelpSetup = lazy(() => import('./pages/HelpSetup').then(m => ({ default: m.HelpSetup })));
const MarketplacePage = lazy(() => import('./pages/MarketplacePage').then(m => ({ default: m.MarketplacePage })));
const MyAgentsPage = lazy(() => import('./pages/MyAgentsPage').then(m => ({ default: m.MyAgentsPage })));
const LandingPage = lazy(() => import('./pages/LandingPage').then(m => ({ default: m.LandingPage })));

// Loading fallback component
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-screen bg-gradient-to-br from-base via-base-secondary to-base-tertiary">
    <div className="text-center">
      <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
      <p className="text-base-primary">Loading...</p>
    </div>
  </div>
);


function Dashboard() {
  const { projectId, branchId } = useParams<{
    projectId?: string;
    branchId?: string;
    taskId?: string;
    subtaskId?: string;
  }>();
  const navigate = useNavigate();
  const { user, tokens } = useAuth();

  // WebSocket is already initialized in AuthContext, no need to duplicate here

  // Derive selection from URL parameters
  const selection = projectId && branchId ? { projectId, branchId } : null;

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLargeScreen, setIsLargeScreen] = useState(false);
  const [showGlobalContext, setShowGlobalContext] = useState(false);
  const [showProjectDetails, setShowProjectDetails] = useState<Project | null>(null);
  const [showBranchDetails, setShowBranchDetails] = useState<{ project: Project; branch: any } | null>(null);

  // Initialize sidebar state based on screen size
  useEffect(() => {
    const handleResize = () => {
      const large = window.innerWidth >= 768; // Changed from 1024 to 768 for better tablet support
      setIsLargeScreen(large);
      // Only auto-open on medium and large screens
      if (large) {
        setSidebarOpen(true);
      }
    };

    // Set initial state
    handleResize();

    // Add event listener
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-base via-base-secondary to-base-tertiary text-base-primary transition-theme">
      {/* Header */}
      <Header />
      
      {/* Main content area */}
      <div className="flex flex-1 relative overflow-hidden">
        {/* Modern Sidebar */}
        <aside className={`
        fixed md:static
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        left-0
        w-full sm:w-80 md:w-1/3 md:min-w-[320px] md:max-w-[400px]
        h-full
        border-r border-surface-border-hover p-3 md:p-4 overflow-y-auto
        bg-surface/95 backdrop-blur-xl
        transition-transform duration-300 ease-in-out
        z-30
        md:translate-x-0
        shadow-xl md:shadow-none
      `}>
        <ProjectList
          onSelect={(projectId: string, branchId: string) => {
            navigate(`/dashboard/project/${projectId}/branch/${branchId}`);
            // Auto-close sidebar on mobile after selection
            if (!isLargeScreen) {
              setSidebarOpen(false);
            }
          }}
          selectedProjectId={projectId}
          selectedBranchId={branchId}
          onShowGlobalContext={() => setShowGlobalContext(true)}
          onShowProjectDetails={(project) => setShowProjectDetails(project)}
          onShowBranchDetails={(project, branch) => setShowBranchDetails({ project, branch })} />
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && !isLargeScreen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Modern Toggle button for mobile */}
      <ShimmerButton
        className={`fixed bottom-6 left-6 z-50 ${isLargeScreen ? 'hidden' : 'block'}`}
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        size="icon"
        variant="default"
        shimmerColor="#3b82f6"
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </ShimmerButton>

        {/* Modern Main content */}
        <main className="flex-1 flex flex-col p-3 md:p-4 lg:p-6 w-full">
           {/* Add padding top on mobile to account for menu button */}
          <div className="flex-1 overflow-y-auto pt-16 md:pt-0">
            {selection ? (
              <LazyTaskList
                projectId={selection.projectId}
                taskTreeId={selection.branchId}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-8">
                  <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl flex items-center justify-center">
                    <Folder className="w-12 h-12 text-primary/60" />
                  </div>
                  <h3 className="text-xl font-semibold text-base-primary mb-3">Choose a workspace</h3>
                  <p className="text-base-secondary max-w-md mx-auto">Select a project and branch from the sidebar to start viewing and managing your tasks.</p>

                  {/* Test notification buttons removed to prevent duplicate notifications */}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
      
      {/* Global Context Dialog - rendered outside all containers */}
      <GlobalContextDialog
        open={showGlobalContext}
        onOpenChange={setShowGlobalContext}
        onClose={() => setShowGlobalContext(false)}
      />
      
      {/* Project Details Dialog - rendered outside all containers */}
      <ProjectDetailsDialog
        open={!!showProjectDetails}
        onOpenChange={(open) => { if (!open) setShowProjectDetails(null); }}
        project={showProjectDetails}
        onClose={() => setShowProjectDetails(null)}
      />
      
      {/* Branch Details Dialog - rendered outside all containers */}
      <BranchDetailsDialog
        open={!!showBranchDetails}
        onOpenChange={(open) => { if (!open) setShowBranchDetails(null); }}
        project={showBranchDetails?.project || null}
        branch={showBranchDetails?.branch || null}
        onClose={() => setShowBranchDetails(null)}
      />
    </div>
  )
}

// Component to conditionally render WebSocketStatusBadge based on authentication
// Placed inside AuthWrapper to have access to AuthContext
function ConditionalWebSocketBadge() {
  const { isAuthenticated } = useAuth();

  // Only show badge when user is authenticated
  if (!isAuthenticated) return null;

  return (
    <Suspense fallback={null}>
      <WebSocketStatusBadge />
    </Suspense>
  );
}

// Home component that shows landing page for anonymous users or redirects to dashboard
function Home() {
  const { isAuthenticated } = useAuth();

  // Redirect authenticated users to dashboard
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  // Show landing page for anonymous users
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LandingPage />
    </Suspense>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
          <Suspense fallback={<LoadingFallback />}>
            <AuthWrapper>
              <ConditionalWebSocketBadge />
              <Routes>
          {/* Public routes with Suspense */}
          <Route path="/login" element={
            <Suspense fallback={<LoadingFallback />}>
              <LoginForm />
            </Suspense>
          } />
          <Route path="/signup" element={
            <Suspense fallback={<LoadingFallback />}>
              <SignupForm />
            </Suspense>
          } />
          <Route path="/registration-success" element={
            <Suspense fallback={<LoadingFallback />}>
              <RegistrationSuccess />
            </Suspense>
          } />
          <Route path="/auth/verify" element={
            <Suspense fallback={<LoadingFallback />}>
              <EmailVerification />
            </Suspense>
          } />
          <Route path="/help-setup" element={
            <Suspense fallback={<LoadingFallback />}>
              <HelpSetup />
            </Suspense>
          } />
          <Route path="/register" element={
            <Suspense fallback={<LoadingFallback />}>
              <SignupForm />
            </Suspense>
          } />

          {/* Protected routes with Suspense */}
          <Route
            path="/dashboard"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/dashboard/project/:projectId"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId/task/:taskId"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId/subtask/:subtaskId"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/profile"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <AppLayout>
                    <Profile />
                  </AppLayout>
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/tokens"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <TokenManagement />
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/agents/marketplace"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <AppLayout>
                    <MarketplacePage />
                  </AppLayout>
                </ProtectedRoute>
              </Suspense>
            }
          />
          <Route
            path="/agents/my-agents"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ProtectedRoute>
                  <AppLayout>
                    <MyAgentsPage />
                  </AppLayout>
                </ProtectedRoute>
              </Suspense>
            }
          />
          {/*<Route
            path="/performance"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <Suspense fallback={<div className="flex items-center justify-center p-8">Loading...</div>}>
                    <PerformanceDashboard />
                  </Suspense>
                </AppLayout>
              </ProtectedRoute>
            }
          />*/}

          {/* Home route - shows landing page for anonymous users or redirects to dashboard */}
          <Route path="/" element={<Home />} />

          {/* Catch-all route for unmatched paths - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </AuthWrapper>
          </Suspense>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;

