import { useNavigate } from 'react-router-dom';
import { ArrowRight, Mic, FileText, Scale, Mail, BarChart3, Shield } from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Mic className="w-8 h-8" />,
      title: "Voice Input",
      subtitle: "Speak in Any Language",
      description: "Tell us your dispute in Hindi, English, or Kannada. Saathi understands you.",
      gradient: "from-orange-500 to-pink-500",
      size: "large"
    },
    {
      icon: <FileText className="w-8 h-8" />,
      title: "Smart OCR",
      subtitle: "Document Extraction",
      description: "Upload invoices, POs, and contracts. We extract all the key details automatically.",
      gradient: "from-blue-500 to-cyan-500",
      size: "medium"
    },
    {
      icon: <Scale className="w-8 h-8" />,
      title: "Legal AI Advisor",
      subtitle: "MSMED Act Expert",
      description: "Get instant advice based on the MSMED Act 2006. Know your rights, calculate interest, understand your options.",
      gradient: "from-green-500 to-emerald-500",
      size: "large"
    },
    {
      icon: <BarChart3 className="w-8 h-8" />,
      title: "Claim Tracker",
      subtitle: "Know Your Progress",
      description: "See real-time completeness of your claim. We tell you exactly what documents you need.",
      gradient: "from-purple-500 to-violet-500",
      size: "medium"
    },
    {
      icon: <Mail className="w-8 h-8" />,
      title: "Demand Notice",
      subtitle: "Auto-Generated Emails",
      description: "Professional demand notices drafted for you. Send directly to the buyer with one click.",
      gradient: "from-yellow-500 to-orange-500",
      size: "medium"
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: "Government Backed",
      subtitle: "MoMSME Initiative",
      description: "Built with Ministry of MSME support. Your data is secure and confidential.",
      gradient: "from-indigo-500 to-blue-500",
      size: "medium"
    }
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-hidden relative">
      {/* Noise Texture Overlay */}
      <div
        className="absolute inset-0 opacity-[0.015] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Mesh Gradient Background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-orange-500/20 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-green-500/15 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/5 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center font-bold text-lg">
              S
            </div>
            <div>
              <h1 className="text-xl font-bold" style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}>
                Saathi <span className="text-orange-400">(साथी)</span>
              </h1>
              <p className="text-xs text-gray-400">Ministry of MSME</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/chat')}
            className="px-4 py-2 rounded-lg bg-white/10 backdrop-blur-lg border border-white/20 hover:bg-white/20 transition-all duration-300 text-sm font-medium"
          >
            Start Your Claim
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-16">
        <div className="text-center max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 backdrop-blur-lg border border-white/10 mb-8">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm text-gray-300">AI-Powered Dispute Resolution</span>
          </div>

          {/* Headline */}
          <h1
            className="text-6xl md:text-7xl font-bold mb-6 leading-tight"
            style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}
          >
            Recover Your{' '}
            <span className="bg-gradient-to-r from-orange-400 via-pink-400 to-purple-400 bg-clip-text text-transparent">
              Delayed Payments
            </span>
            {' '}with AI
          </h1>

          {/* Subheadline */}
          <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Saathi is your AI companion for filing MSME payment disputes.
            Speak in your language, upload documents, get expert legal advice — all in one conversation.
          </p>

          {/* CTA Buttons */}
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => navigate('/chat')}
              className="group px-8 py-4 rounded-xl bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 transition-all duration-300 font-semibold text-lg flex items-center gap-2 shadow-2xl shadow-orange-500/20"
            >
              Start Your Claim
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <button
              onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}
              className="px-8 py-4 rounded-xl bg-white/5 backdrop-blur-lg border border-white/10 hover:bg-white/10 transition-all duration-300 font-semibold text-lg"
            >
              Learn More
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 mt-16 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-4xl font-bold bg-gradient-to-r from-orange-400 to-pink-400 bg-clip-text text-transparent mb-2">
                3
              </div>
              <div className="text-sm text-gray-400">Languages Supported</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-2">
                100%
              </div>
              <div className="text-sm text-gray-400">MSMED Act Compliant</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent mb-2">
                5 min
              </div>
              <div className="text-sm text-gray-400">To File Your Claim</div>
            </div>
          </div>
        </div>
      </section>

      {/* Bento Grid Features */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2
            className="text-5xl font-bold mb-4"
            style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}
          >
            Everything You Need to{' '}
            <span className="bg-gradient-to-r from-orange-400 to-pink-400 bg-clip-text text-transparent">
              Win Your Claim
            </span>
          </h2>
          <p className="text-gray-400 text-lg">
            Powered by OpenAI GPT-4, Whisper, and MSMED Act 2006 knowledge base
          </p>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[240px]">
          {features.map((feature, index) => (
            <div
              key={index}
              className={`
                group relative overflow-hidden rounded-2xl
                backdrop-blur-xl bg-white/5 border border-white/10
                hover:border-white/20 hover:bg-white/10
                transition-all duration-500
                ${feature.size === 'large' ? 'md:col-span-2 md:row-span-1' : 'md:col-span-1'}
              `}
            >
              {/* Card Gradient Overlay */}
              <div
                className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-500`}
              />

              {/* Content */}
              <div className="relative z-10 p-8 h-full flex flex-col">
                {/* Icon */}
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  {feature.icon}
                </div>

                {/* Text */}
                <div className="flex-1">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                    {feature.subtitle}
                  </div>
                  <h3 className="text-2xl font-bold mb-3" style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}>
                    {feature.title}
                  </h3>
                  <p className="text-gray-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>

                {/* Hover Arrow */}
                <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <ArrowRight className="w-5 h-5 text-white/60" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2
            className="text-5xl font-bold mb-4"
            style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}
          >
            File Your Claim in{' '}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              3 Simple Steps
            </span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              step: "01",
              title: "Tell Saathi Your Story",
              description: "Type or speak about your payment dispute. Saathi understands Hindi, English, and Kannada.",
              gradient: "from-orange-500 to-pink-500"
            },
            {
              step: "02",
              title: "Upload Documents",
              description: "Share your invoices, POs, and contracts. Our AI extracts all important details automatically.",
              gradient: "from-blue-500 to-cyan-500"
            },
            {
              step: "03",
              title: "Send Demand Notice",
              description: "Review AI-drafted email and send to buyer. Track claim progress and get negotiation advice.",
              gradient: "from-green-500 to-emerald-500"
            }
          ].map((step, index) => (
            <div key={index} className="relative group">
              {/* Connector Line (except last) */}
              {index < 2 && (
                <div className="hidden md:block absolute top-12 left-full w-full h-0.5 bg-gradient-to-r from-white/20 to-transparent" />
              )}

              {/* Step Card */}
              <div className="relative backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-8 group-hover:bg-white/10 group-hover:border-white/20 transition-all duration-300">
                <div className={`text-6xl font-bold bg-gradient-to-r ${step.gradient} bg-clip-text text-transparent mb-4`}>
                  {step.step}
                </div>
                <h3 className="text-2xl font-bold mb-3" style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}>
                  {step.title}
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="relative overflow-hidden rounded-3xl backdrop-blur-xl bg-gradient-to-br from-orange-500/10 via-pink-500/10 to-purple-500/10 border border-white/10 p-16 text-center">
          {/* Background glow */}
          <div className="absolute -top-1/2 -left-1/2 w-96 h-96 bg-orange-500/20 rounded-full blur-[100px]" />
          <div className="absolute -bottom-1/2 -right-1/2 w-96 h-96 bg-pink-500/20 rounded-full blur-[100px]" />

          <div className="relative z-10">
            <h2
              className="text-5xl font-bold mb-6"
              style={{ fontFamily: 'Space Grotesk, system-ui, sans-serif' }}
            >
              Ready to Recover Your Payments?
            </h2>
            <p className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto">
              Join thousands of MSMEs using Saathi to file payment disputes under the MSMED Act 2006.
            </p>
            <button
              onClick={() => navigate('/chat')}
              className="group px-10 py-5 rounded-xl bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 transition-all duration-300 font-bold text-xl flex items-center gap-3 mx-auto shadow-2xl shadow-orange-500/30"
            >
              Start Your Claim Now
              <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-pink-500 flex items-center justify-center font-bold text-lg">
                  S
                </div>
                <div>
                  <h3 className="font-bold text-lg">Saathi (साथी)</h3>
                  <p className="text-xs text-gray-400">Ministry of MSME</p>
                </div>
              </div>
              <p className="text-gray-400 text-sm leading-relaxed max-w-md">
                AI-powered dispute resolution assistant helping MSMEs recover delayed payments under the MSMED Act 2006.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><button onClick={() => navigate('/chat')} className="hover:text-white transition-colors">Start Claim</button></li>
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#" className="hover:text-white transition-colors">FAQ</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">MSMED Act 2006</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/5 mt-12 pt-8 text-center text-sm text-gray-400">
            <p>Built with AI Kosh Initiative • Powered by OpenAI • © 2026 Ministry of MSME</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
