import { Folder, Menu, X } from 'lucide-react';
import { lazy, Suspense, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Project } from './api';
import './App.css';
import { AppLayout } from './components/AppLayout';
import { AuthWrapper, EmailVerification, LoginForm, ProtectedRoute, SignupForm } from './components/auth';
import BranchDetailsDialog from './components/BranchDetailsDialog';
import GlobalContextDialog from './components/GlobalContextDialog';
import { Header } from './components/Header';
import ProjectDetailsDialog from './components/ProjectDetailsDialog';
import ProjectList from './components/ProjectList';
import { Button } from './components/ui/button';
import ShimmerButton from './components/ui/ShimmerButton';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './components/ui/toast';
import { Profile } from './pages/Profile';
import RegistrationSuccess from './pages/RegistrationSuccess';
import { TokenManagement } from './pages/TokenManagement';

// Use lazy loading for TaskList component for better performance
const LazyTaskList = lazy(() => import('./components/LazyTaskList'));
const PerformanceDashboard = lazy(() => import('./components/PerformanceDashboard'));

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
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        left-0
        w-full sm:w-96 lg:w-1/3 lg:min-w-[400px] lg:max-w-[500px]
        h-full
        border-r border-surface-border-hover p-4 sm:p-6 overflow-y-auto
        bg-surface/95 backdrop-blur-xl
        transition-transform duration-300 ease-in-out
        z-30
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
          <Route
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

