"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Brand, Icon, type IconName } from "@/components/ui";

const LINKS: { href: string; label: string; icon: IconName }[] = [
  { href: "/dashboard", label: "Overview", icon: "grid" },
  { href: "/profile", label: "My profile", icon: "user" },
  { href: "/world", label: "My world", icon: "world" },
  { href: "/settings", label: "Settings", icon: "settings" },
];

export default function Nav({ username }: { username: string }) {
  const pathname = usePathname();
  const router = useRouter();
  async function signOut() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }
  return (
    <aside className="sidebar" aria-label="Workspace navigation">
      <Link
        href="/dashboard"
        className="sidebar-brand"
        aria-label="Athena overview"
      >
        <Brand />
      </Link>
      <p className="nav-label">Workspace</p>
      <nav className="main-nav">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link ${pathname.startsWith(link.href) ? "active" : ""}`}
            aria-current={pathname.startsWith(link.href) ? "page" : undefined}
          >
            <Icon name={link.icon} />
            <span>{link.label}</span>
          </Link>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-note">
          <Icon name="spark" />
          <h3>Small steps. Real progress.</h3>
          <p>Every application adds something to your world.</p>
          <Link href="/world">
            See your world <Icon name="arrow" size={14} />
          </Link>
        </div>
        <div className="account">
          <span className="avatar">{username.slice(0, 2).toUpperCase()}</span>
          <div className="account-info">
            <strong title={username}>{username}</strong>
            <span>Personal workspace</span>
          </div>
          <button
            onClick={signOut}
            className="icon-button"
            aria-label="Sign out"
            title="Sign out"
          >
            <Icon name="logout" size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
}
