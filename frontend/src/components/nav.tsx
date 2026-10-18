"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Brand, Icon, type IconName } from "@/components/ui";
import Avatar from "@/components/avatar";
import type { AvatarName } from "@/lib/types";

const LINKS: { href: string; label: string; icon: IconName }[] = [
  { href: "/dashboard", label: "Overview", icon: "grid" },
  { href: "/profile", label: "My profile", icon: "user" },
  { href: "/world", label: "My world", icon: "world" },
  { href: "/settings", label: "Settings", icon: "settings" },
];
// Hiding this from members is presentation only — /admin redirects and
// every /admin endpoint refuses a non-admin regardless of the menu.
const ADMIN_LINK: { href: string; label: string; icon: IconName } = {
  href: "/admin",
  label: "Administration",
  icon: "shield",
};

export default function Nav({
  username,
  avatar,
  isAdmin = false,
}: {
  username: string;
  avatar: AvatarName;
  isAdmin?: boolean;
}) {
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
        {[...LINKS, ...(isAdmin ? [ADMIN_LINK] : [])].map((link) => (
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
        <div className="account">
          <Avatar name={avatar} size={34} />
          <div className="account-info">
            <strong title={username}>{username}</strong>
            <span>{isAdmin ? "Administrator" : "Personal workspace"}</span>
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
