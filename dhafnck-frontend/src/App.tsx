import { useState, useEffect, lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import ProjectList from './components/ProjectList';
import { Button } from './components/ui/button';
import { Menu, X, Folder } from 'lucide-react';
import { AuthWrapper, LoginForm, SignupForm, ProtectedRoute, EmailVerification } from './components/auth';
import { Header } from './components/Header';
import { Profile } from './pages/Profile';
import { TokenManagement } from './pages/TokenManagement';
import RegistrationSuccess from './pages/RegistrationSuccess';
import { AppLayout } from './components/AppLayout';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './components/ui/toast';
import GlobalContextDialog from './components/GlobalContextDialog';
import ProjectDetailsDialog from './components/ProjectDetailsDialog';
import BranchDetailsDialog from './components/BranchDetailsDialog';
import { Project } from './api';

// Use lazy loading for TaskList component for better performance
const LazyTaskList = lazy(() => import('./components/LazyTaskList'));

function Dashboard() {
  const [selection, setSelection] = useState<{ projectId: string, branchId: string } | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLargeScreen, setIsLargeScreen] = useState(false);
  const [projectListRefreshKey, setProjectListRefreshKey] = useState(0);
  const [showGlobalContext, setShowGlobalContext] = useState(false);
  const [showProjectDetails, setShowProjectDetails] = useState<Project | null>(null);
  const [showBranchDetails, setShowBranchDetails] = useState<{ project: Project; branch: any } | null>(null);

  // Initialize sidebar state based on screen size
  useEffect(() => {
    const handleResize = () => {
      const large = window.innerWidth >= 1024;
      setIsLargeScreen(large);
      // Only auto-open on large screens
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
        fixed lg:static
        ${sidebarOpen ? 'left-0' : '-left-full'}
        w-96 lg:w-1/3 lg:min-w-[400px] lg:max-w-[500px]
        h-full
        border-r border-surface-border-hover p-6 overflow-y-auto
        bg-surface/95 backdrop-blur-xl
        transition-all duration-300 ease-in-out
        z-20
        lg:translate-x-0
        shadow-xl lg:shadow-none
      `}>
        <ProjectList 
          refreshKey={projectListRefreshKey}
          onSelect={(projectId: string, branchId: string) => {
            setSelection({ projectId, branchId });
            // Auto-close sidebar on mobile after selection
            if (!isLargeScreen) {
              setSidebarOpen(false);
            }
          }}
          onShowGlobalContext={() => setShowGlobalContext(true)}
          onShowProjectDetails={(project) => setShowProjectDetails(project)}
          onShowBranchDetails={(project, branch) => setShowBranchDetails({ project, branch })} />
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && !isLargeScreen && (
        <div 
          className="fixed inset-0 bg-black/50 z-10 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Modern Toggle button for mobile */}
      {!isLargeScreen && (
        <Button
          variant="outline"
          size="icon"
          className={`fixed z-30 lg:hidden bg-surface/95 backdrop-blur-xl border-2 border-surface-border-hover shadow-xl hover:shadow-2xl transition-all duration-300 rounded-2xl ${
            sidebarOpen ? 'top-6 right-6' : 'top-6 left-6'
          }`}
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      )}

        {/* Modern Main content */}
        <main className="flex-1 flex flex-col p-6 w-full">
          {/* Add padding top on mobile to account for menu button */}
          <div className="flex-1 overflow-y-auto pt-16 lg:pt-0">
            {selection ? (
              <Suspense fallback={
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary/20 border-t-primary mx-auto mb-6"></div>
                    <p className="text-base-secondary text-lg font-medium">Loading tasks...</p>
                    <p className="text-base-tertiary text-sm mt-2">Please wait while we fetch your data</p>
                  </div>
                </div>
              }>
                <LazyTaskList 
                key={`${selection.projectId}-${selection.branchId}`} 
                projectId={selection.projectId} 
                taskTreeId={selection.branchId} 
                onTasksChanged={() => {
                console.log('App: onTasksChanged called, incrementing refreshKey');
                setProjectListRefreshKey(prev => prev + 1);
              }}
            />
              </Suspense>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-8">
                  <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl flex items-center justify-center">
                    <Folder className="w-12 h-12 text-primary/60" />
                  </div>
                  <h3 className="text-xl font-semibold text-base-primary mb-3">Choose a workspace</h3>
                  <p className="text-base-secondary max-w-md mx-auto">Select a project and branch from the sidebar to start viewing and managing your tasks.</p>
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
    <ThemeProvider>
      <ToastProvider>
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
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </AuthWrapper>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;

