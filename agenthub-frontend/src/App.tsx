import { Folder, Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useParams, useNavigate } from 'react-router-dom';
import { Project } from './api';
import './App.css';
import './styles/animations.css';
import './styles/websocket-animations.css';
import { AppLayout } from './components/AppLayout';
import { AuthWrapper, EmailVerification, LoginForm, ProtectedRoute, SignupForm } from './components/auth';
import BranchDetailsDialog from './components/BranchDetailsDialog';
import GlobalContextDialog from './components/GlobalContextDialog';
import { Header } from './components/Header';
import ProjectDetailsDialog from './components/ProjectDetailsDialog';
import ProjectList from './components/ProjectList';
import ShimmerButton from './components/ui/ShimmerButton';
import { ToastProvider } from './components/ui/toast';
import { WebSocketToastBridge } from './components/WebSocketToastBridge';
import { ThemeProvider } from './contexts/ThemeContext';
// Import Redux Provider and store
import { Provider as ReduxProvider } from 'react-redux';
import { store } from './store';
// Import WebSocket v2.0 hook for new implementation
import { useWebSocket } from './hooks/useWebSocketV2';
import { useAuth } from './contexts/AuthContext';
// Import toastEventBus for testing
import { toastEventBus } from './services/toastEventBus';
import { useToast } from './components/ui/toast';
import { Profile } from './pages/Profile';
import RegistrationSuccess from './pages/RegistrationSuccess';
import { TokenManagement } from './pages/TokenManagement';
import { HelpSetup } from './pages/HelpSetup';
// Use lazy loading for TaskList component for better performance
import LazyTaskList from './components/LazyTaskList';
//const PerformanceDashboard = lazy(() => import('./components/PerformanceDashboard'));

// TEMPORARY: Animation diagnostic component for debugging
import AnimationDiagnostic from './components/AnimationDiagnostic';

function Dashboard() {
  const { projectId, branchId } = useParams<{
    projectId?: string;
    branchId?: string;
    taskId?: string;
    subtaskId?: string;
  }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user, tokens } = useAuth();

  // Initialize WebSocket v2.0 connection
  useWebSocket(user?.id || '', tokens?.access_token || '');

  // Derive selection from URL parameters
  const selection = projectId && branchId ? { projectId, branchId } : null;

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLargeScreen, setIsLargeScreen] = useState(false);
  const [projectListRefreshKey, setProjectListRefreshKey] = useState(0);
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
          refreshKey={projectListRefreshKey}
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
                onTasksChanged={() => {
                  setProjectListRefreshKey(prev => prev + 1);
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-8">
                  <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl flex items-center justify-center">
                    <Folder className="w-12 h-12 text-primary/60" />
                  </div>
                  <h3 className="text-xl font-semibold text-base-primary mb-3">Choose a workspace</h3>
                  <p className="text-base-secondary max-w-md mx-auto">Select a project and branch from the sidebar to start viewing and managing your tasks.</p>

                  {/* Temporary debug button to test notifications */}
                  <div className="mt-8 space-y-2">
                    <p className="text-sm text-base-secondary">Debug: Test Notifications</p>
                    <div className="flex gap-2 justify-center">
                      <button
                        onClick={() => {
                          console.log('🧪 TEST: Triggering success notification via toastEventBus');
                          toastEventBus.success('Test Success', 'This is a test success notification');
                        }}
                        className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"
                      >
                        Test Success
                      </button>
                      <button
                        onClick={() => {
                          console.log('🧪 TEST: Triggering error notification via toastEventBus');
                          toastEventBus.error('Test Error', 'This is a test error notification');
                        }}
                        className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
                      >
                        Test Error
                      </button>
                      <button
                        onClick={() => {
                          console.log('🧪 TEST: Triggering direct showToast call');
                          showToast({
                            type: 'info',
                            title: 'Direct Toast',
                            description: 'This is a direct showToast call'
                          });
                        }}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                      >
                        Direct Toast
                      </button>
                    </div>
                  </div>

                  {/* TEMPORARY: Animation Diagnostic for debugging */}
                  <AnimationDiagnostic />
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

function App() {
  return (
    <ReduxProvider store={store}>
      <ThemeProvider>
        <ToastProvider>
          <WebSocketToastBridge />
          <AuthWrapper>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginForm />} />
          <Route path="/signup" element={<SignupForm />} />
          <Route path="/registration-success" element={<RegistrationSuccess />} />
          <Route path="/auth/verify" element={<EmailVerification />} />
          
          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/project/:projectId"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId/task/:taskId"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/project/:projectId/branch/:branchId/task/:taskId/subtask/:subtaskId"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <Profile />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tokens"
            element={
              <ProtectedRoute>
                <TokenManagement />
              </ProtectedRoute>
            }
          />
          <Route
            path="/help"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <HelpSetup />
                </AppLayout>
              </ProtectedRoute>
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
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </AuthWrapper>
      </ToastProvider>
    </ThemeProvider>
    </ReduxProvider>
  );
}

export default App;

