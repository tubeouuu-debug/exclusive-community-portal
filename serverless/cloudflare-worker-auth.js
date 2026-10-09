/**
 * Cloudflare Worker: Discord OAuth2 Authentication Gatekeeper
 * 
 * Verifies that the authenticating user belongs to the target Discord server
 * and holds the required VIP role before granting access.
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Configuration via Cloudflare Worker Environment Variables
    const CLIENT_ID = env.DISCORD_CLIENT_ID || 'YOUR_DISCORD_CLIENT_ID';
    const CLIENT_SECRET = env.DISCORD_CLIENT_SECRET || 'YOUR_DISCORD_CLIENT_SECRET';
    const GUILD_ID = env.DISCORD_GUILD_ID || 'YOUR_TARGET_SERVER_GUILD_ID';
    const REQUIRED_ROLE_ID = env.DISCORD_REQUIRED_ROLE_ID || null; // Optional: specify VIP role ID
    const FRONTEND_URL = env.FRONTEND_URL || 'https://your-frontend-domain.pages.dev';
    const REDIRECT_URI = `${url.origin}/callback`;

    // 1. ROUTE /login: Redirect user to Discord OAuth2 Authorize page
    if (url.pathname === '/login' || url.pathname === '/api/auth/login') {
      const discordAuthUrl = new URL('https://discord.com/api/oauth2/authorize');
      discordAuthUrl.searchParams.set('client_id', CLIENT_ID);
      discordAuthUrl.searchParams.set('redirect_uri', REDIRECT_URI);
      discordAuthUrl.searchParams.set('response_type', 'code');
      discordAuthUrl.searchParams.set('scope', 'identify guilds guilds.members.read');
      discordAuthUrl.searchParams.set('prompt', 'consent');
      return Response.redirect(discordAuthUrl.toString(), 302);
    }

    // 2. ROUTE /callback: Exchange authorization code for token & verify membership
    if (url.pathname === '/callback' || url.pathname === '/api/auth/callback') {
      const code = url.searchParams.get('code');
      const error = url.searchParams.get('error');

      if (error || !code) {
        return Response.redirect(`${FRONTEND_URL}/?auth_error=access_denied`, 302);
      }

      try {
        // Exchange code for Access Token
        const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            grant_type: 'authorization_code',
            code: code,
            redirect_uri: REDIRECT_URI
          })
        });

        if (!tokenRes.ok) {
          return Response.redirect(`${FRONTEND_URL}/?auth_error=token_failed`, 302);
        }

        const tokenData = await tokenRes.json();
        const accessToken = tokenData.access_token;

        // Fetch User Identity (@me)
        const userRes = await fetch('https://discord.com/api/users/@me', {
          headers: { Authorization: `Bearer ${accessToken}` }
        });
        const user = await userRes.json();

        // Verify Guild Membership
        const guildsRes = await fetch('https://discord.com/api/users/@me/guilds', {
          headers: { Authorization: `Bearer ${accessToken}` }
        });
        const guilds = await guildsRes.json();
        const isInGuild = Array.isArray(guilds) && guilds.some(g => g.id === GUILD_ID);

        if (!isInGuild) {
          const uName = encodeURIComponent(user.global_name || user.username);
          return Response.redirect(`${FRONTEND_URL}/?auth_error=not_in_server&name=${uName}`, 302);
        }

        // Success: Redirect back with safe user metadata for dynamic watermarking
        const avatarUrl = user.avatar 
          ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
          : `https://cdn.discordapp.com/embed/avatars/${parseInt(user.discriminator || '0') % 5}.png`;

        const successParams = new URLSearchParams({
          auth_success: '1',
          uid: user.id,
          uname: encodeURIComponent(user.global_name || user.username),
          uavatar: encodeURIComponent(avatarUrl)
        });

        return Response.redirect(`${FRONTEND_URL}/?${successParams.toString()}`, 302);

      } catch (err) {
        console.error('OAuth Callback Error:', err);
        return Response.redirect(`${FRONTEND_URL}/?auth_error=server_error`, 302);
      }
    }

    return new Response(JSON.stringify({ status: 'ok', service: 'Discord Auth Gatekeeper' }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
