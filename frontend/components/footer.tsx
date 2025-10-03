import { ProximaLogo } from "@/components/proxima-logo"
import { Github, Linkedin, Mail, Twitter } from "lucide-react"
import Link from "next/link"

export function Footer() {
    const navItems = [
        { href: "/predictions", label: "Career Predictions" },
        { href: "/similarity", label: "Player Similarity" },
        { href: "/compare", label: "Compare Players" },
        { href: "/teams", label: "Team Analysis" },
        { href: "/community", label: "Community" },
    ]

    const legalLinks = [
        { href: "/privacy", label: "Privacy Policy" },
        { href: "/terms", label: "Terms of Service" },
        { href: "/cookies", label: "Cookie Policy" },
    ]

    const socialLinks = [
        { href: "https://twitter.com/proximafootball", icon: Twitter, label: "Twitter" },
        { href: "https://github.com/proximafootball", icon: Github, label: "GitHub" },
        { href: "https://linkedin.com/company/proximafootball", icon: Linkedin, label: "LinkedIn" },
        { href: "mailto:contact@proximafootball.ai", icon: Mail, label: "Email" },
    ]

    return (
        <footer className="bg-card border-t border-border">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                    {/* Brand Section */}
                    <div className="col-span-1 md:col-span-2">
                        <Link href="/" className="flex items-center space-x-3 group mb-4">
                            <ProximaLogo />
                        </Link>
                        <p className="text-muted-foreground text-sm max-w-md mb-6">
                            Advanced AI-powered football analytics, player predictions, and career insights. Discover the future of
                            football with cutting-edge artificial intelligence.
                        </p>
                        <div className="flex space-x-4">
                            {socialLinks.map((social) => {
                                const Icon = social.icon
                                return (
                                    <Link
                                        key={social.href}
                                        href={social.href}
                                        className="text-muted-foreground hover:text-primary transition-colors duration-200"
                                        aria-label={social.label}
                                    >
                                        <Icon className="h-5 w-5" />
                                    </Link>
                                )
                            })}
                        </div>
                    </div>

                    {/* Navigation Links */}
                    <div>
                        <h3 className="text-foreground font-semibold mb-4">Platform</h3>
                        <ul className="space-y-2">
                            {navItems.map((item) => (
                                <li key={item.href}>
                                    <Link
                                        href={item.href}
                                        className="text-muted-foreground hover:text-primary transition-colors duration-200 text-sm"
                                    >
                                        {item.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Legal Links */}
                    <div>
                        <h3 className="text-foreground font-semibold mb-4">Legal</h3>
                        <ul className="space-y-2">
                            {legalLinks.map((item) => (
                                <li key={item.href}>
                                    <Link
                                        href={item.href}
                                        className="text-muted-foreground hover:text-primary transition-colors duration-200 text-sm"
                                    >
                                        {item.label}
                                    </Link>
                                </li>
                            ))}
                            <li>
                                <Link
                                    href="/about"
                                    className="text-muted-foreground hover:text-primary transition-colors duration-200 text-sm"
                                >
                                    About Us
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/contact"
                                    className="text-muted-foreground hover:text-primary transition-colors duration-200 text-sm"
                                >
                                    Contact
                                </Link>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Bottom Section */}
                <div className="mt-8 pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center">
                    <p className="text-muted-foreground text-sm">
                        © {new Date().getFullYear()} Proxima Football AI. All rights reserved.
                    </p>
                    <p className="text-muted-foreground text-sm mt-2 md:mt-0">
                        Powered by <a href="https://www.symantriq.com" target="_blank" className="text-white">Symantriq</a>
                    </p>
                </div>
            </div>
        </footer>
    )
}
