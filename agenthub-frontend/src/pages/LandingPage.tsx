import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import {
  Brain,
  Code,
  Zap,
  Shield,
  Cpu,
  Globe,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Users,
  Clock,
  Server,
  Moon,
  Sun,
  TestTube,
  Github,
  MessageCircle,
  Heart,
  GitPullRequest,
  Coffee,
  Terminal
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export const LandingPage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  // Comprehensive SEO optimization
  useEffect(() => {
    // Title
    document.title = '4genthub - AI Development Platform | 32 Specialized AI Agents for Developers';

    // Helper function to update or create meta tags
    const updateMeta = (name: string, content: string, property?: boolean) => {
      const attribute = property ? 'property' : 'name';
      const selector = `meta[${attribute}="${name}"]`;
      let meta = document.querySelector(selector);

      if (meta) {
        meta.setAttribute('content', content);
      } else {
        meta = document.createElement('meta');
        meta.setAttribute(attribute, name);
        meta.setAttribute('content', content);
        document.head.appendChild(meta);
      }
    };

    // Basic SEO Meta Tags
    updateMeta('description', 'Transform your development workflow with 4genthub - enterprise-grade MCP platform featuring 32 specialized AI agents for coding, testing, debugging, security auditing, DevOps automation, and more. Start free trial today.');
    updateMeta('keywords', 'AI agents, MCP platform, development tools, code generation, automated testing, AI coding assistant, Claude integration, enterprise AI, developer productivity, DevOps automation, CI/CD, security scanning, code review AI');
    updateMeta('author', '4genthub');
    updateMeta('robots', 'index, follow');

    // Open Graph Meta Tags (Facebook, LinkedIn)
    updateMeta('og:title', '4genthub - 32 Specialized AI Agents for Modern Development', true);
    updateMeta('og:description', 'Enterprise-grade MCP platform with AI agents for coding, testing, security, DevOps, and more. Cloud or self-hosted. Setup in 2 minutes.', true);
    updateMeta('og:type', 'website', true);
    updateMeta('og:url', 'https://www.4genthub.com', true);
    updateMeta('og:image', 'https://www.4genthub.com/og-image.png', true);
    updateMeta('og:site_name', '4genthub', true);
    updateMeta('og:locale', 'en_US', true);

    // Twitter Card Meta Tags
    updateMeta('twitter:card', 'summary_large_image');
    updateMeta('twitter:title', '4genthub - AI Development Platform with 32 Specialized Agents');
    updateMeta('twitter:description', 'Enterprise MCP platform featuring specialized AI agents for every development task. Cloud or self-hosted. Free trial available.');
    updateMeta('twitter:image', 'https://www.4genthub.com/twitter-card.png');
    updateMeta('twitter:site', '@4genthub');

    // Canonical URL
    let canonical = document.querySelector('link[rel="canonical"]') as HTMLLinkElement;
    if (canonical) {
      canonical.href = 'https://www.4genthub.com';
    } else {
      canonical = document.createElement('link');
      canonical.rel = 'canonical';
      canonical.href = 'https://www.4genthub.com';
      document.head.appendChild(canonical);
    }

    // Structured Data (JSON-LD) for Google Rich Results
    const structuredData = {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "4genthub",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Web, Cloud, Linux, macOS, Windows",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD",
        "description": "Free trial available"
      },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "127"
      },
      "description": "Enterprise-grade MCP platform featuring 32 specialized AI agents for coding, testing, debugging, security auditing, and DevOps automation. Integrates with Claude Code for AI-powered development workflows.",
      "featureList": [
        "32 Specialized AI Agents",
        "Claude Code Integration",
        "Automated Code Generation",
        "Security Auditing",
        "DevOps Automation",
        "Cloud or Self-Hosted Deployment",
        "4-Tier Context Management",
        "Real-time Collaboration"
      ],
      "screenshot": "https://www.4genthub.com/screenshot.png",
      "softwareVersion": "2.0",
      "author": {
        "@type": "Organization",
        "name": "4genthub",
        "url": "https://www.4genthub.com"
      }
    };

    let scriptTag = document.querySelector('script[type="application/ld+json"]');
    if (scriptTag) {
      scriptTag.textContent = JSON.stringify(structuredData);
    } else {
      scriptTag = document.createElement('script');
      scriptTag.type = 'application/ld+json';
      scriptTag.textContent = JSON.stringify(structuredData);
      document.head.appendChild(scriptTag);
    }

    // Cleanup function
    return () => {
      // Optionally clean up meta tags when component unmounts
    };
  }, []);

  const features = [
    {
      icon: <Brain className="h-8 w-8 text-purple-500" />,
      title: '32 Specialized AI Agents',
      description: 'From coding and testing to security auditing and DevOps - each agent is an expert in its domain.'
    },
    {
      icon: <Zap className="h-8 w-8 text-yellow-500" />,
      title: 'Lightning Fast Development',
      description: 'Automate repetitive tasks, generate code, write tests, and debug issues 10x faster than manual work.'
    },
    {
      icon: <Shield className="h-8 w-8 text-green-500" />,
      title: 'Enterprise Security',
      description: 'Built-in security agents scan for vulnerabilities, audit code, and ensure compliance with best practices.'
    },
    {
      icon: <Globe className="h-8 w-8 text-blue-500" />,
      title: 'Cloud or Self-Hosted',
      description: 'Deploy on our managed cloud infrastructure or run on your own servers for complete data control.'
    },
    {
      icon: <Code className="h-8 w-8 text-orange-500" />,
      title: 'Claude Code Integration',
      description: 'Seamlessly integrates with Claude Code via MCP protocol for natural AI-powered development workflows.'
    },
    {
      icon: <Cpu className="h-8 w-8 text-red-500" />,
      title: '4-Tier Context System',
      description: 'Intelligent context management across Global → Project → Branch → Task levels for optimal AI performance.'
    }
  ];

  const agents = [
    'Coding Agent', 'Test Orchestrator', 'Debugger Agent', 'Security Auditor',
    'Code Reviewer', 'DevOps Agent', 'Database Agent', 'API Agent',
    'Frontend Agent', 'Backend Agent', 'Mobile Agent', 'Documentation Agent',
    'Performance Agent', 'Architecture Agent', 'ML/AI Agent', 'Data Agent',
    '...and 16 more specialized agents'
  ];

  const howItWorks = [
    {
      step: '1',
      title: 'Sign Up & Get API Key',
      description: 'Create your account and get instant access to your API credentials.',
      icon: <Users className="h-6 w-6" />
    },
    {
      step: '2',
      title: 'Configure MCP Client',
      description: 'Add your API key to Claude Code configuration - takes less than 2 minutes.',
      icon: <Server className="h-6 w-6" />
    },
    {
      step: '3',
      title: 'Create Your Agents',
      description: 'Use default templates or create all 32 specialized agents from your dashboard.',
      icon: <Brain className="h-6 w-6" />
    },
    {
      step: '4',
      title: 'Start Building',
      description: 'Interact naturally with Claude Code - agents handle the rest automatically.',
      icon: <Sparkles className="h-6 w-6" />
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Navigation Header */}
      <nav className="sticky top-0 z-50 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center space-x-2">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
                  <Brain className="h-6 w-6 text-white" />
                </div>
                <span className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  4genthub
                </span>
              </Link>
            </div>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center space-x-8">
              <Link to="/help-setup" className="text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                Documentation
              </Link>
              <Link to="/agents/marketplace" className="text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                Marketplace
              </Link>
              <a href="https://github.com/phamhung075/4genthub-hooks" target="_blank" rel="noopener noreferrer" className="text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                GitHub
              </a>
            </div>

            {/* Theme Toggle & Auth Buttons */}
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="text-gray-600 dark:text-gray-300"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </Button>
              <Link to="/login">
                <Button variant="ghost" className="text-gray-700 dark:text-gray-300">
                  Sign In
                </Button>
              </Link>
              <Link to="/register">
                <Button className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white">
                  Start Free Trial
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-blue-500/10 dark:from-purple-900/20 dark:to-blue-900/20" />
        <div className="max-w-7xl mx-auto px-6 py-20 sm:py-32 relative">
          <div className="text-center">
            <h1 className="text-5xl sm:text-7xl font-bold text-gray-900 dark:text-gray-100 mb-6">
              Transform Development with
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-600 dark:from-purple-400 dark:to-blue-400">
                32 AI Agents
              </span>
            </h1>
            <p className="text-xl sm:text-2xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
              Enterprise-grade MCP platform that supercharges your development workflow with specialized AI agents for every task
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link to="/register">
                <Button size="lg" className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-6 text-lg">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link to="/help-setup">
                <Button size="lg" variant="outline" className="px-8 py-6 text-lg">
                  View Documentation
                </Button>
              </Link>
            </div>
            <div className="mt-6 space-y-2">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                <Clock className="inline h-4 w-4 mr-1" />
                Setup in under 2 minutes • No credit card required
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Already have an account?{' '}
                <Link to="/login" className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-semibold underline">
                  Sign in here
                </Link>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* AI Compatibility Section */}
      <section className="py-16 bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-900 dark:to-indigo-900">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center text-white">
            <h2 className="text-3xl font-bold mb-4">
              🤖 Works with Your Favorite AI Tools
            </h2>
            <p className="text-lg text-purple-100 mb-8 max-w-3xl mx-auto">
              4genthub is <strong>AI-agnostic</strong> and compatible with any AI client that supports MCP (Model Context Protocol)
            </p>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <Card className="p-6 bg-white/10 backdrop-blur-sm border-2 border-white/20 hover:bg-white/20 transition-all">
                <div className="flex items-center justify-center gap-3 mb-3">
                  <Terminal className="h-8 w-8 text-white" />
                  <h3 className="text-xl font-bold text-white">Claude Code</h3>
                </div>
                <p className="text-sm text-purple-100">
                  Official Anthropic CLI with full MCP support and hook system integration
                </p>
              </Card>

              <Card className="p-6 bg-white/10 backdrop-blur-sm border-2 border-white/20 hover:bg-white/20 transition-all">
                <div className="flex items-center justify-center gap-3 mb-3">
                  <Code className="h-8 w-8 text-white" />
                  <h3 className="text-xl font-bold text-white">Cursor IDE</h3>
                </div>
                <p className="text-sm text-purple-100">
                  AI-powered code editor with native MCP tool integration
                </p>
              </Card>

              <Card className="p-6 bg-white/10 backdrop-blur-sm border-2 border-white/20 hover:bg-white/20 transition-all">
                <div className="flex items-center justify-center gap-3 mb-3">
                  <Cpu className="h-8 w-8 text-white" />
                  <h3 className="text-xl font-bold text-white">OpenAI Codex</h3>
                </div>
                <p className="text-sm text-purple-100">
                  GPT-4, o1, and all OpenAI models with tool/function calling capabilities
                </p>
              </Card>
            </div>

            <div className="bg-white/10 backdrop-blur-sm border-2 border-white/20 rounded-lg p-6">
              <h4 className="font-bold text-lg mb-3 flex items-center justify-center gap-2">
                <Sparkles className="h-5 w-5" />
                Universal AI Model Support
              </h4>
              <p className="text-purple-100 text-sm max-w-3xl mx-auto">
                Compatible with <strong>any AI model</strong> that supports tool/function calling:
                GPT-4, Claude 3.5, Gemini, Llama 3, Mistral, Qwen, and more.
                If your AI can use tools, it can use 4genthub!
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Everything You Need to Build Faster
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Professional-grade tools trusted by developers worldwide
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="p-6 hover:shadow-lg transition-shadow">
                <div className="mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  {feature.description}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* AI Agents Showcase */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              32 Specialized AI Agents
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Each agent is an expert in its domain, ready to assist you
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {agents.map((agent, index) => (
              <div
                key={index}
                className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center"
              >
                <CheckCircle2 className="h-5 w-5 text-green-500 mr-3 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                  {agent}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Get Started in 4 Simple Steps
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              From signup to production in minutes
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {howItWorks.map((item, index) => (
              <div key={index} className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 text-white text-2xl font-bold mb-4">
                  {item.step}
                </div>
                <div className="mb-2 flex justify-center text-purple-600 dark:text-purple-400">
                  {item.icon}
                </div>
                <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                  {item.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Beta Testing Section */}
      <section className="py-20 bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-950/50 dark:to-indigo-950/50 border-y border-purple-200 dark:border-purple-800">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-purple-600 dark:bg-purple-700 text-white px-6 py-2 rounded-full mb-6 font-semibold">
              <TestTube className="h-5 w-5" />
              BETA VERSION - PUBLIC TESTING
            </div>
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              🚀 Join Our Beta Testing Program
            </h2>
            <p className="text-xl text-gray-700 dark:text-gray-300 max-w-3xl mx-auto">
              We're in beta and welcome all developers to test <strong>100% free</strong> and help us build the future of AI-powered development!
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <Card className="p-6 bg-white dark:bg-gray-800 border-2 border-purple-200 dark:border-purple-700 hover:border-purple-400 dark:hover:border-purple-500 transition-colors">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">100% Free Access</h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                Full access to all 32 AI agents, features, and updates during beta. No hidden costs, no credit card required.
              </p>
            </Card>

            <Card className="p-6 bg-white dark:bg-gray-800 border-2 border-purple-200 dark:border-purple-700 hover:border-purple-400 dark:hover:border-purple-500 transition-colors">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                  <Users className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Shape the Future</h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                Your feedback directly influences features and improvements. Be part of the development journey.
              </p>
            </Card>

            <Card className="p-6 bg-white dark:bg-gray-800 border-2 border-purple-200 dark:border-purple-700 hover:border-purple-400 dark:hover:border-purple-500 transition-colors">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                  <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Early Access</h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                Get first access to new agents, features, and capabilities before public release.
              </p>
            </Card>
          </div>

          <Card className="p-8 bg-gradient-to-r from-gray-900 to-gray-800 dark:from-gray-950 dark:to-gray-900 text-white border-2 border-gray-700 dark:border-gray-600">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex-1">
                <h3 className="text-2xl font-bold mb-3 flex items-center gap-2">
                  <Github className="h-7 w-7" />
                  Open Source & Community Driven
                </h3>
                <p className="text-gray-300 dark:text-gray-400 mb-4">
                  4genthub is <strong>publicly shared</strong> and open to contributions! Help improve the codebase,
                  report bugs, suggest features, and collaborate with developers worldwide.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a href="https://github.com/phamhung075/4genthub-hooks" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" className="bg-white dark:bg-gray-100 text-gray-900 hover:bg-gray-100 dark:hover:bg-gray-200">
                      <Github className="mr-2 h-4 w-4" />
                      View Source Code
                    </Button>
                  </a>
                  <a href="https://github.com/phamhung075/4genthub-hooks/issues" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" className="border-white text-white hover:bg-white/10 dark:hover:bg-white/20">
                      <MessageCircle className="mr-2 h-4 w-4" />
                      Report Issues & Feedback
                    </Button>
                  </a>
                  <a href="https://discord.gg/zmhMpK6N" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" className="border-white text-white hover:bg-white/10 dark:hover:bg-white/20">
                      <MessageCircle className="mr-2 h-4 w-4" />
                      Join Discord
                    </Button>
                  </a>
                </div>
              </div>
            </div>
          </Card>

          <div className="mt-8 text-center">
            <Link to="/register">
              <Button size="lg" className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white px-10 py-6 text-lg shadow-lg hover:shadow-xl transition-shadow">
                <TestTube className="mr-2 h-5 w-5" />
                Join Beta Testing Now - Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-4">
              No credit card required • Full feature access • Community support
            </p>
          </div>
        </div>
      </section>

      {/* Deployment Options */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Choose Your Deployment
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Cloud-hosted or self-hosted - you decide
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <Card className="p-8 border-2 border-purple-500 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-purple-500 text-white px-4 py-1 text-sm font-semibold">
                RECOMMENDED
              </div>
              <Globe className="h-12 w-12 text-purple-500 mb-4" />
              <h3 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
                ☁️ Cloud Hosted
              </h3>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">Setup in under 2 minutes</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">Automatic updates & scaling</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">24/7 enterprise support</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">99.9% uptime SLA</span>
                </li>
              </ul>
              <Link to="/register">
                <Button className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700">
                  Start Cloud Trial
                </Button>
              </Link>
            </Card>

            <Card className="p-8">
              <Server className="h-12 w-12 text-blue-500 mb-4" />
              <h3 className="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
                💻 Self-Hosted
              </h3>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">Complete data control</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">No internet dependency</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">Customize everything</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle2 className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-700 dark:text-gray-300">One-time setup</span>
                </li>
              </ul>
              <Link to="/help-setup">
                <Button variant="outline" className="w-full">
                  View Setup Guide
                </Button>
              </Link>
            </Card>
          </div>
        </div>
      </section>

      {/* Community Support & Contribution Section */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-2 rounded-full mb-6 font-semibold shadow-lg">
              <Heart className="h-5 w-5 fill-white" />
              SUPPORT THE PROJECT
            </div>
            <h2 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              💝 Help Us Keep 4genthub Free for Everyone
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-6">
              4genthub is <strong>100% free</strong> and will always be. Help us cover server costs and keep developing amazing features for the community!
            </p>

            {/* Personal Story */}
            <Card className="max-w-4xl mx-auto p-6 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-950/30 dark:to-indigo-950/30 border-2 border-purple-200 dark:border-purple-800">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-purple-600 dark:bg-purple-700 flex items-center justify-center">
                    <Code className="h-6 w-6 text-white" />
                  </div>
                </div>
                <div className="text-left">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">
                    ❤️ Built with Love by a Solo Developer
                  </h3>
                  <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                    I'm a single developer who <strong>loves coding</strong> but struggles to find employment.
                    This project was born from <strong>pure passion</strong> for creating tools that help other developers.
                    Every line of code, every feature, every bug fix comes from my dedication to building something meaningful
                    for the community. Your support doesn't just keep the servers running—it validates that this work matters
                    and helps me continue doing what I love. 🙏
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <div className="grid md:grid-cols-2 gap-8 mb-12">
            {/* Donation Card */}
            <Card className="p-8 bg-white dark:bg-gray-800 border-2 border-purple-200 dark:border-purple-800 hover:border-purple-400 dark:hover:border-purple-600 transition-all hover:shadow-xl">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/50 mb-4">
                  <Heart className="h-8 w-8 text-purple-600 dark:text-purple-400 fill-purple-600 dark:fill-purple-400" />
                </div>
                <h3 className="text-2xl font-bold mb-3 text-gray-900 dark:text-gray-100">
                  💰 Support via Donations
                </h3>
                <p className="text-gray-600 dark:text-gray-300 mb-6">
                  Running servers, databases, and infrastructure costs money. Every contribution helps keep 4genthub online and <strong>free for everyone</strong>.
                </p>

                <div className="space-y-3 mb-6">
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                    <Coffee className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span>☕ Buy us a coffee → Keeps server running for 1 day</span>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                    <Server className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <span>🖥️ Sponsor hosting → Covers monthly server costs</span>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                    <Zap className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    <span>⚡ Power development → New features & agents</span>
                  </div>
                </div>

                <div className="bg-purple-50 dark:bg-purple-950/30 p-4 rounded-lg border border-purple-200 dark:border-purple-800 mb-6">
                  <p className="text-sm text-purple-900 dark:text-purple-100 font-semibold mb-2">
                    🎯 Current Server Status
                  </p>
                  <p className="text-xs text-purple-800 dark:text-purple-200">
                    Running on volunteer resources • All donations go directly to infrastructure costs • 100% transparent usage reports
                  </p>
                </div>

                <div className="space-y-3">
                  <a href="https://buymeacoffee.com/daihungpham" target="_blank" rel="noopener noreferrer">
                    <Button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-shadow">
                      <Coffee className="mr-2 h-5 w-5" />
                      Buy Me a Coffee
                    </Button>
                  </a>
                  <a href="https://github.com/sponsors/phamhung075" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" className="w-full border-purple-300 text-purple-700 hover:bg-purple-50 dark:border-purple-700 dark:text-purple-300 dark:hover:bg-purple-950/30">
                      <Heart className="mr-2 h-5 w-5 fill-current" />
                      GitHub Sponsors
                    </Button>
                  </a>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-3">
                  One-time or monthly • Cancel anytime • Secure payments
                </p>
              </div>
            </Card>

            {/* Code Contribution Card */}
            <Card className="p-8 bg-white dark:bg-gray-800 border-2 border-indigo-200 dark:border-indigo-800 hover:border-indigo-400 dark:hover:border-indigo-600 transition-all hover:shadow-xl">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-900/50 mb-4">
                  <GitPullRequest className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h3 className="text-2xl font-bold mb-3 text-gray-900 dark:text-gray-100">
                  🚀 Contribute Code
                </h3>
                <p className="text-gray-600 dark:text-gray-300 mb-6">
                  Help improve 4genthub! The codebase is <strong>100% open source</strong> and publicly accessible. All skill levels welcome!
                </p>

                <div className="space-y-3 mb-6 text-left">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Fix Bugs & Issues</p>
                      <p className="text-xs text-gray-600 dark:text-gray-300">Check our issue tracker for beginner-friendly tasks</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Build New Features</p>
                      <p className="text-xs text-gray-600 dark:text-gray-300">Propose and implement new capabilities</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Create New Agents</p>
                      <p className="text-xs text-gray-600 dark:text-gray-300">Design specialized AI agents for specific tasks</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Improve Documentation</p>
                      <p className="text-xs text-gray-600 dark:text-gray-300">Help others learn and understand the platform</p>
                    </div>
                  </div>
                </div>

                <div className="bg-indigo-50 dark:bg-indigo-950/30 p-4 rounded-lg border border-indigo-200 dark:border-indigo-800 mb-6">
                  <p className="text-sm text-indigo-900 dark:text-indigo-100 font-semibold mb-2">
                    🌟 Contributing Benefits
                  </p>
                  <p className="text-xs text-indigo-800 dark:text-indigo-200">
                    Build your portfolio • Learn from experienced developers • Shape the future of AI development tools
                  </p>
                </div>

                <div className="space-y-3">
                  <a href="https://github.com/phamhung075/4genthub-hooks" target="_blank" rel="noopener noreferrer">
                    <Button className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-shadow">
                      <Github className="mr-2 h-5 w-5" />
                      Browse Source Code
                    </Button>
                  </a>
                  <a href="https://github.com/phamhung075/4genthub-hooks/issues" target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" className="w-full border-indigo-300 text-indigo-700 hover:bg-indigo-50 dark:border-indigo-700 dark:text-indigo-300 dark:hover:bg-indigo-950/30">
                      <GitPullRequest className="mr-2 h-5 w-5" />
                      View Open Issues
                    </Button>
                  </a>
                </div>
              </div>
            </Card>
          </div>

          {/* Community Stats */}
          <Card className="p-6 bg-gradient-to-r from-purple-600 to-indigo-600 dark:from-purple-900 dark:to-indigo-900 text-white text-center shadow-xl">
            <p className="text-lg mb-3">
              <strong>Together, we're building something amazing!</strong>
            </p>
            <div className="flex flex-wrap justify-center gap-8 text-sm">
              <div>
                <p className="text-3xl font-bold text-white">100%</p>
                <p className="text-purple-100">Free Forever</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">32</p>
                <p className="text-purple-100">AI Agents</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">Open</p>
                <p className="text-purple-100">Source Code</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">❤️</p>
                <p className="text-purple-100">Community Driven</p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-purple-600 to-blue-600 dark:from-purple-800 dark:to-blue-900 text-white">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl font-bold mb-4">
            Ready to Transform Your Development Workflow?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of developers using 4genthub to build faster and smarter
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register">
              <Button size="lg" className="bg-white dark:bg-gray-100 text-purple-600 dark:text-purple-700 hover:bg-gray-100 dark:hover:bg-gray-200 px-8 py-6 text-lg">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 dark:hover:bg-white/20 px-8 py-6 text-lg">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 dark:bg-gray-950 text-gray-300 dark:text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-white dark:text-gray-100 font-bold text-xl mb-4">4genthub</h3>
              <p className="text-sm">
                Enterprise AI platform with 32 specialized agents for modern development teams.
              </p>
            </div>
            <div>
              <h4 className="text-white dark:text-gray-100 font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/help-setup" className="hover:text-white dark:hover:text-gray-100 transition-colors">Features</Link></li>
                <li><Link to="/help-setup" className="hover:text-white dark:hover:text-gray-100 transition-colors">Documentation</Link></li>
                <li><Link to="/agents/marketplace" className="hover:text-white dark:hover:text-gray-100 transition-colors">Agent Marketplace</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white dark:text-gray-100 font-semibold mb-4">Resources</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/help-setup" className="hover:text-white dark:hover:text-gray-100 transition-colors">Getting Started</Link></li>
                <li><a href="https://docs.4genthub.com" target="_blank" rel="noopener noreferrer" className="hover:text-white dark:hover:text-gray-100 transition-colors">API Docs</a></li>
                <li><a href="https://github.com/phamhung075/4genthub-hooks" target="_blank" rel="noopener noreferrer" className="hover:text-white dark:hover:text-gray-100 transition-colors">GitHub</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white dark:text-gray-100 font-semibold mb-4">Community</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="https://discord.gg/zmhMpK6N" target="_blank" rel="noopener noreferrer" className="hover:text-white dark:hover:text-gray-100 transition-colors">Discord</a></li>
                <li><a href="https://github.com/phamhung075/4genthub-hooks/issues" target="_blank" rel="noopener noreferrer" className="hover:text-white dark:hover:text-gray-100 transition-colors">Report Issues</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 dark:border-gray-700 mt-8 pt-8 text-center text-sm">
            <p>&copy; 2025 4genthub. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
