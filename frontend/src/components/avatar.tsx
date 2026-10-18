import type { AvatarName } from "@/lib/types";

/** The five faces, drawn rather than fetched — a few hundred bytes of
 * inline SVG each, no image requests, and they stay crisp at the 28px the
 * sidebar uses and the 64px the picker does. The database stores only the
 * key (see supabase/migrations/0003_profile_identity.sql). */
export const AVATARS: { name: AvatarName; label: string }[] = [
  { name: "fox", label: "Fox" },
  { name: "owl", label: "Owl" },
  { name: "cat", label: "Cat" },
  { name: "bear", label: "Bear" },
  { name: "fawn", label: "Fawn" },
];

/** `soft` is the tile behind the face, so each avatar reads as its own
 * chip even at sidebar size. */
const faces: Record<AvatarName, { soft: string; art: React.ReactNode }> = {
  fox: {
    soft: "#ffe3cd",
    art: (
      <>
        <path d="M14 23 17 8l12 9Zm36 0L47 8 35 17Z" fill="#f08a4b" />
        <path d="M17.5 20 19 12.5l6.5 5Zm29 0L45 12.5l-6.5 5Z" fill="#ffd3b5" />
        <path d="M32 15c11 0 18 7.5 18 17.5C50 43 42.5 51 32 51S14 43 14 32.5C14 22.5 21 15 32 15Z" fill="#f08a4b" />
        <path d="M32 29c7.5 0 13 4.5 13 10.5C45 46 39 51 32 51s-13-5-13-11.5C19 33.5 24.5 29 32 29Z" fill="#fff4ea" />
        <ellipse cx="24.5" cy="31.5" rx="2.6" ry="3" fill="#3b2c26" />
        <ellipse cx="39.5" cy="31.5" rx="2.6" ry="3" fill="#3b2c26" />
        <path d="M32 38.5c2 0 3.2 1.2 3.2 2.4 0 1.6-1.6 2.6-3.2 2.6s-3.2-1-3.2-2.6c0-1.2 1.2-2.4 3.2-2.4Z" fill="#3b2c26" />
      </>
    ),
  },
  owl: {
    soft: "#e2e6fb",
    art: (
      <>
        <path d="M18 17.5 15.5 10l7.5 4Zm28 0L48.5 10 41 14Z" fill="#6c79c4" />
        <path d="M32 13c10.5 0 18 8 18 19.5S42.5 52 32 52s-18-8-18-19.5S21.5 13 32 13Z" fill="#7f8cd6" />
        <path d="M32 31c6 0 10.5 4 10.5 10.5S38 52 32 52s-10.5-4-10.5-10.5S26 31 32 31Z" fill="#e2e6fb" />
        <circle cx="24.5" cy="29" r="7.5" fill="#fff8ec" />
        <circle cx="39.5" cy="29" r="7.5" fill="#fff8ec" />
        <circle cx="24.5" cy="29.5" r="3.4" fill="#3b2c26" />
        <circle cx="39.5" cy="29.5" r="3.4" fill="#3b2c26" />
        <path d="m32 33.5 3.6 4.2h-7.2Z" fill="#f0a94b" />
      </>
    ),
  },
  cat: {
    soft: "#eef0f5",
    art: (
      <>
        <path d="M16 24 16.5 9l11 7.5Zm32 0L47.5 9l-11 7.5Z" fill="#9aa3b2" />
        <path d="M19.5 20.5 20 13l5.5 4Zm25 0L44 13l-5.5 4Z" fill="#f3c3cb" />
        <path d="M32 15c10.5 0 18 7.5 18 18S42.5 51 32 51s-18-7.5-18-18 7.5-18 18-18Z" fill="#9aa3b2" />
        <ellipse cx="24" cy="31" rx="2.6" ry="3.4" fill="#3b2c26" />
        <ellipse cx="40" cy="31" rx="2.6" ry="3.4" fill="#3b2c26" />
        <path d="m32 36.5 2.6 2h-5.2Z" fill="#f3a0ae" />
        <path d="M32 38.5v2.5m0 0c0 2-2 3-3.8 3m3.8-3c0 2 2 3 3.8 3" stroke="#3b2c26" strokeWidth="1.6" strokeLinecap="round" fill="none" />
        <path d="M20 33h-6m6 3.5-5.5 2M44 33h6m-6 3.5 5.5 2" stroke="#6f7a8c" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity=".55" />
      </>
    ),
  },
  bear: {
    soft: "#f0ddc9",
    art: (
      <>
        <circle cx="19" cy="19" r="7" fill="#a87c56" />
        <circle cx="45" cy="19" r="7" fill="#a87c56" />
        <circle cx="19" cy="19" r="3.4" fill="#f0ddc9" />
        <circle cx="45" cy="19" r="3.4" fill="#f0ddc9" />
        <path d="M32 15c10.5 0 18 7.5 18 18S42.5 51 32 51s-18-7.5-18-18 7.5-18 18-18Z" fill="#a87c56" />
        <ellipse cx="32" cy="39" rx="10" ry="8" fill="#f0ddc9" />
        <circle cx="24.5" cy="31" r="2.9" fill="#3b2c26" />
        <circle cx="39.5" cy="31" r="2.9" fill="#3b2c26" />
        <ellipse cx="32" cy="36.5" rx="3.4" ry="2.6" fill="#3b2c26" />
        <path d="M32 39v2m0 0c0 1.6-1.7 2.6-3.3 2.6M32 41c0 1.6 1.7 2.6 3.3 2.6" stroke="#3b2c26" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      </>
    ),
  },
  fawn: {
    soft: "#fbeada",
    art: (
      <>
        <path d="M21 16c-2-3-5-4-7.5-3.5M21 16c-3.5-.5-5.5 1-6 3M43 16c2-3 5-4 7.5-3.5M43 16c3.5-.5 5.5 1 6 3" stroke="#8a6440" strokeWidth="2.4" strokeLinecap="round" fill="none" />
        <ellipse cx="17.5" cy="25" rx="4" ry="6" fill="#d9a066" transform="rotate(-20 17.5 25)" />
        <ellipse cx="46.5" cy="25" rx="4" ry="6" fill="#d9a066" transform="rotate(20 46.5 25)" />
        <path d="M32 17c9.5 0 16.5 7 16.5 17S41.5 51 32 51s-16.5-7-16.5-17 7-17 16.5-17Z" fill="#d9a066" />
        <ellipse cx="32" cy="41" rx="8.5" ry="7" fill="#fbeada" />
        <circle cx="25" cy="32" r="2.8" fill="#3b2c26" />
        <circle cx="39" cy="32" r="2.8" fill="#3b2c26" />
        <ellipse cx="32" cy="39" rx="3" ry="2.3" fill="#3b2c26" />
        <circle cx="22" cy="25" r="1.6" fill="#fbeada" />
        <circle cx="27" cy="22" r="1.3" fill="#fbeada" />
        <circle cx="42" cy="25" r="1.6" fill="#fbeada" />
        <circle cx="37" cy="22" r="1.3" fill="#fbeada" />
      </>
    ),
  },
};

export default function Avatar({
  name,
  size = 36,
  className = "",
}: {
  name: AvatarName;
  size?: number;
  className?: string;
}) {
  const face = faces[name] ?? faces.fox;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-hidden="true"
      className={`avatar-art ${className}`}
      style={{ background: face.soft }}
    >
      {face.art}
    </svg>
  );
}
