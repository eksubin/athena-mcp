import Link from "next/link";
import { Brand, Icon } from "@/components/ui";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Athena — A calmer job search",
  description:
    "One thoughtful space for your opportunities, resume, and application progress. Find your next chapter with Athena.",
};

export default function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link href="/" aria-label="Athena home">
          <Brand />
        </Link>
        <nav aria-label="Main navigation">
          <a href="#how-it-works" className="landing-nav-link">
            How it works
          </a>
          <Link href="/login" className="button button-secondary">
            Sign in <Icon name="arrow" size={15} />
          </Link>
        </nav>
      </header>
      <main>
        <section className="landing-hero">
          <p className="eyebrow">A little clarity for your next big step</p>
          <h1>
            Your next chapter.
            <br />
            <span>A little more organized.</span>
          </h1>
          <p>
            A home for the roles you find, the story you tell,
            <br className="desktop-break" /> and the progress you make along the
            way.
          </p>
          <div className="landing-actions">
            <Link href="/login" className="button button-primary">
              Find your next with Athena <Icon name="arrow" size={17} />
            </Link>
            <a href="#how-it-works" className="button button-quiet">
              Take a look around
            </a>
          </div>
          <p className="landing-reassurance">
            <Icon name="shield" size={14} /> Your search is personal. Your
            details stay private.
          </p>
        </section>
        <section className="landing-product" aria-label="The Athena workflow">
          <div className="landing-product-top">
            <div>
              <p className="eyebrow">Less scattered. More intentional.</p>
              <h2>A place for every possibility.</h2>
            </div>
            <span className="pill">Your personal workspace</span>
          </div>
          <div className="landing-flow">
            <div>
              <span className="flow-number">01</span>
              <Icon name="briefcase" size={23} />
              <h3>Collect the possibilities</h3>
              <p>Keep promising roles together, ready for your next move.</p>
            </div>
            <div>
              <span className="flow-number">02</span>
              <Icon name="file" size={23} />
              <h3>Tell your story</h3>
              <p>Your resume and thoughtful answers, ready when you are.</p>
            </div>
            <div>
              <span className="flow-number">03</span>
              <Icon name="world" size={23} />
              <h3>See yourself grow</h3>
              <p>Follow every application and watch your world take shape.</p>
            </div>
          </div>
          <div className="landing-stages">
            <span>Saved</span>
            <Icon name="arrow" size={14} />
            <span>Applied</span>
            <Icon name="arrow" size={14} />
            <span>Interview</span>
            <Icon name="arrow" size={14} />
            <span>Your next chapter</span>
          </div>
        </section>
        <section className="landing-details" id="how-it-works">
          <div>
            <p className="eyebrow">Built around your search</p>
            <h2>
              More room to focus
              <br />
              on what comes next.
            </h2>
          </div>
          <div className="landing-feature-list">
            <article>
              <Icon name="grid" />
              <div>
                <h3>One clear view</h3>
                <p>
                  Move applications from saved to offer. Search your pipeline
                  and always know where things stand.
                </p>
              </div>
            </article>
            <article>
              <Icon name="spark" />
              <div>
                <h3>A little help from your assistant</h3>
                <p>
                  Connect your assistant to discover roles, save opportunities,
                  and keep your applications up to date.
                </p>
              </div>
            </article>
            <article>
              <Icon name="shield" />
              <div>
                <h3>Your story stays yours</h3>
                <p>
                  Your resume and answers are private. In the shared world,
                  neighbors see only your chosen identity and progress.
                </p>
              </div>
            </article>
          </div>
        </section>
        <section className="landing-closing">
          <h2>Make space for your next.</h2>
          <Link className="button button-primary" href="/login">
            Get started <Icon name="arrow" size={16} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Brand />
        <p>A thoughtful space for your next chapter.</p>
        <Link href="/login">
          Your workspace <Icon name="arrow" size={14} />
        </Link>
      </footer>
    </div>
  );
}
