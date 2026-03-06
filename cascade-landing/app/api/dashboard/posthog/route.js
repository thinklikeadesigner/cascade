import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

const PH_KEY = process.env.POSTHOG_PERSONAL_API_KEY;
const PH_HOST = "https://us.i.posthog.com";
const PROJECT_ID = "324431";

async function fetchPH(path) {
  const res = await fetch(`${PH_HOST}/api/projects/${PROJECT_ID}${path}`, {
    headers: { Authorization: `Bearer ${PH_KEY}` },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    console.error(`PostHog ${path}: ${res.status}`, body);
    throw new Error(`PostHog ${path}: ${res.status}`);
  }
  return res.json();
}

export async function GET() {
  if (process.env.NODE_ENV !== "development") {
    return new Response("Not found", { status: 404 });
  }
  if (!PH_KEY) {
    return Response.json({ error: "Missing POSTHOG_PERSONAL_API_KEY" }, { status: 500 });
  }

  try {
    const [eventsData, personsData] = await Promise.all([
      fetchPH("/events/?limit=100"),
      fetchPH("/persons/?limit=100"),
    ]);

    const events = eventsData.results || [];
    const persons = (personsData.results || []);

    // Filter out MagicMock test persons
    const realPersons = persons.filter(
      (p) => !p.distinct_ids.some((id) => String(id).includes("MagicMock"))
    );

    // Build distinct_id → email lookup from PostHog persons
    const idToEmail = {};
    for (const p of persons) {
      const email = p.properties?.email;
      if (email) {
        for (const id of p.distinct_ids) {
          idToEmail[String(id)] = email;
        }
      }
    }

    // Cross-reference with Supabase auth users for emails PostHog doesn't have
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    if (supabaseUrl && supabaseServiceKey) {
      try {
        const supabase = createClient(supabaseUrl, supabaseServiceKey, {
          auth: { autoRefreshToken: false, persistSession: false },
        });
        const { data: authUsers } = await supabase.auth.admin.listUsers();
        for (const u of (authUsers?.users || [])) {
          if (u.email) {
            // Supabase user ID is used as PostHog distinct_id after identify()
            idToEmail[u.id] = u.email;
          }
        }

        // Also check tenants table — NanoClaw uses tenant IDs and telegram user IDs
        const { data: tenants } = await supabase
          .from("tenants")
          .select("id, telegram_user_id, user_id")
          .limit(100);

        for (const t of (tenants || [])) {
          const email = idToEmail[t.user_id]; // user_id → email from auth
          if (email) {
            if (t.id) idToEmail[String(t.id)] = email;
            if (t.telegram_user_id) idToEmail[String(t.telegram_user_id)] = email;
            // Also map "tenant-N" style IDs
            idToEmail[`tenant-${t.id}`] = email;
          }
        }
      } catch (err) {
        console.error("Supabase cross-ref failed:", err.message);
      }
    }

    function resolveUser(distinctId) {
      const id = String(distinctId);
      return idToEmail[id] || id.slice(0, 16);
    }

    // Event breakdown
    const eventCounts = {};
    const customEvents = [];
    const pageviews = [];

    for (const e of events) {
      const name = e.event;
      eventCounts[name] = (eventCounts[name] || 0) + 1;

      if (!name.startsWith("$")) {
        customEvents.push({
          event: name,
          timestamp: e.timestamp,
          person: resolveUser(e.distinct_id),
          properties: Object.fromEntries(
            Object.entries(e.properties || {}).filter(([k]) => !k.startsWith("$"))
          ),
        });
      }

      if (name === "$pageview") {
        const url = e.properties?.$current_url || e.properties?.["$current_url"] || "";
        pageviews.push({
          timestamp: e.timestamp,
          url,
          person: resolveUser(e.distinct_id),
        });
      }
    }

    // Page breakdown from pageviews
    const pageCounts = {};
    for (const pv of pageviews) {
      try {
        const path = new URL(pv.url).pathname;
        pageCounts[path] = (pageCounts[path] || 0) + 1;
      } catch {
        pageCounts[pv.url] = (pageCounts[pv.url] || 0) + 1;
      }
    }

    // Persons with their properties (enriched with Supabase emails)
    const users = realPersons.map((p) => {
      const props = p.properties || {};
      // Try PostHog email first, then cross-ref any distinct_id against Supabase
      let email = props.email || null;
      if (!email) {
        for (const id of p.distinct_ids) {
          if (idToEmail[String(id)]) { email = idToEmail[String(id)]; break; }
        }
      }
      return {
        distinctIds: p.distinct_ids.slice(0, 3),
        email,
        browser: props.$browser || null,
        os: props.$os || null,
        country: props.$geoip_country_name || null,
        city: props.$geoip_city_name || null,
        createdAt: p.created_at,
      };
    });

    return Response.json({
      totalEvents: events.length,
      eventCounts,
      customEvents: customEvents.slice(0, 20),
      pageCounts,
      pageviews: pageviews.slice(0, 20),
      users,
      totalPersons: personsData.count || persons.length,
      realPersons: realPersons.length,
      testPersons: persons.length - realPersons.length,
    });
  } catch (err) {
    console.error("PostHog API error:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
