import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { 
  TrendingUp, 
  BarChart3, 
  ShieldCheck, 
  Cpu, 
  ArrowRight,
  ChevronRight,
  Globe,
  Zap
} from 'lucide-react';
import heroBg from '../assets/hero-bg.png';

const Landing = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.6, ease: "easeOut" }
    }
  };

  const features = [
    {
      icon: <Cpu className="w-8 h-8 text-blue-500" />,
      title: "Advanced ML Models",
      description: "Utilizing LSTM, ARIMA, and Linear Regression for high-precision price forecasting."
    },
    {
      icon: <BarChart3 className="w-8 h-8 text-purple-500" />,
      title: "Real-time Tracking",
      description: "Monitor your portfolio performance with live data streams and instant updates."
    },
    {
      icon: <ShieldCheck className="w-8 h-8 text-emerald-500" />,
      title: "Portfolio Security",
      description: "Enterprise-grade security to keep your financial data and strategies protected."
    },
    {
      icon: <Zap className="w-8 h-8 text-amber-500" />,
      title: "Instant Analytics",
      description: "Get deep insights into market trends and model accuracy with a single click."
    }
  ];

  return (
    <div className="min-h-screen bg-[#0a0c10] text-white selection:bg-blue-500/30">
      {/* Hero Section */}
      <section className="relative h-[90vh] min-h-[600px] flex items-center justify-center overflow-hidden">
        {/* Background Image with Overlay */}
        <div className="absolute inset-0 z-0">
          <img 
            src={heroBg} 
            alt="Hero Background" 
            className="w-full h-full object-cover opacity-40 scale-105 animate-pulse-slow"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-[#0a0c10]/20 via-[#0a0c10]/60 to-[#0a0c10]"></div>
        </div>

        {/* Hero Content */}
        <motion.div 
          className="relative z-10 max-w-5xl px-6 text-center"
          initial="hidden"
          animate="visible"
          variants={containerVariants}
        >
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-medium mb-6">
            <Globe className="w-4 h-4" />
            <span>AI-Powered Quantitative Analysis</span>
          </motion.div>
          
          <motion.h1 
            variants={itemVariants}
            className="text-5xl md:text-7xl font-bold mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-white to-gray-500"
          >
            Predict the Future of <br /> 
            <span className="text-blue-500">Stock Markets</span>
          </motion.h1>
          
          <motion.p 
            variants={itemVariants}
            className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed"
          >
            Empower your investment strategy with state-of-the-art machine learning models. 
            Analyze, predict, and optimize your portfolio in real-time.
          </motion.p>
          
          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link 
              to="/register" 
              className="group relative px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all duration-300 flex items-center gap-2 overflow-hidden"
            >
              <span className="relative z-10">Start Analyzing Now</span>
              <ArrowRight className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform" />
              <div className="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </Link>
            
            <Link 
              to="/login" 
              className="px-8 py-4 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl border border-white/10 transition-all backdrop-blur-sm"
            >
              Sign In
            </Link>
          </motion.div>
        </motion.div>

        {/* Decorative elements */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-gray-500 animate-bounce cursor-pointer">
          <span className="text-xs uppercase tracking-widest font-semibold">Scroll to explore</span>
          <ChevronRight className="w-5 h-5 rotate-90" />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 max-w-7xl mx-auto relative z-10 bg-[#0a0c10]">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Sophisticated Engine</h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Our platform combines classical financial theories with cutting-edge neural networks 
            to provide unmatched market clarity.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="p-8 rounded-2xl bg-[#131722]/80 border border-white/5 hover:border-blue-500/30 transition-all hover:bg-[#131722] group backdrop-blur-sm"
            >
              <div className="mb-6 p-3 rounded-lg bg-white/5 w-fit group-hover:scale-110 transition-transform">
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-gray-400 leading-relaxed text-sm">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer / CTA Section */}
      <section className="py-24 px-6 border-t border-white/5 bg-[#0a0c10]">
        <div className="max-w-4xl mx-auto p-12 rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-700 relative overflow-hidden text-center shadow-[0_0_50px_rgba(37,99,235,0.2)]">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 blur-3xl -translate-y-1/2 translate-x-1/2 rounded-full"></div>
          <div className="relative z-10">
            <h2 className="text-3xl md:text-5xl font-bold mb-6 italic">Stay Ahead of the Market Curve</h2>
            <p className="text-blue-100 text-lg mb-10 max-w-xl mx-auto">
              Join thousands of quantitative analysts using our platform to gain a competitive edge in the global markets.
            </p>
            <Link 
              to="/register" 
              className="inline-block px-10 py-4 bg-white text-blue-600 font-bold rounded-xl hover:shadow-xl hover:scale-105 transition-all text-lg"
            >
              Unlock Free Trial
            </Link>
          </div>
        </div>
        
        <div className="mt-24 text-center text-gray-500 text-sm">
          <div className="flex justify-center gap-8 mb-8">
            <span className="hover:text-gray-300 transition-colors cursor-pointer">Terms of Service</span>
            <span className="hover:text-gray-300 transition-colors cursor-pointer">Privacy Policy</span>
            <span className="hover:text-gray-300 transition-colors cursor-pointer">Support</span>
          </div>
          <p>© 2026 Bizmetric Stock Analysis Labs. All rights reserved.</p>
        </div>
      </section>

      <style jsx>{`
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.4; transform: scale(1.05); }
          50% { opacity: 0.5; transform: scale(1.0); }
        }
        .animate-pulse-slow {
          animation: pulse-slow 8s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default Landing;
