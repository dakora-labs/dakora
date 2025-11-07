export default function Footer() {
  const links = [
    { label: "Docs", href: "https://docs.dakora.io" },
    { label: "GitHub", href: "https://github.com/dakora-labs/dakora" },
    { label: "Discord", href: "https://discord.gg/QSRRcFjzE8" },
    { label: "Twitter", href: "https://twitter.com/dakora" },
    { label: "Privacy Policy", href: "/privacy" },
  ];

  return (
    <footer className="bg-white border-t border-gray-200 py-8 px-6">
      <div className="container mx-auto max-w-7xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <p className="text-sm text-gray-600">
              © 2025 Dakora. All rights reserved.
            </p>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <img
                src="/eu-flag.jpg"
                alt="EU Flag"
                className="w-5 h-5 rounded-sm object-cover"
              />
              <span>Built in the EU</span>
            </div>
          </div>
          <div className="flex gap-6">
            {links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                target={link.href.startsWith('http') ? '_blank' : undefined}
                rel={link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                className="text-sm text-gray-600 hover:text-blue-500 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
