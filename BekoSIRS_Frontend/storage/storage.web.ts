// Web platform storage using localStorage
// This file is used when running in web mode (Expo web)

const TOKEN_KEY = 'authToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

// Save access token
export async function saveToken(token: string): Promise<void> {
  try {
    if (!token) {
      if (__DEV__) console.warn('⚠️ Attempted to save empty token');
      return;
    }
    localStorage.setItem(TOKEN_KEY, token);
    if (__DEV__) console.log('✅ Token saved successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error saving token (web):', error);
    throw error;
  }
}

// Get access token
export async function getToken(): Promise<string | null> {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      if (__DEV__) console.log('✅ Token retrieved successfully (web)');
    } else {
      if (__DEV__) console.log('ℹ️ No token found (web)');
    }
    return token;
  } catch (error) {
    if (__DEV__) console.error('❌ Error getting token (web):', error);
    return null;
  }
}

// Delete access token
export async function deleteToken(): Promise<void> {
  try {
    localStorage.removeItem(TOKEN_KEY);
    if (__DEV__) console.log('✅ Token deleted successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error deleting token (web):', error);
    // Don't throw to prevent blocking logout
  }
}

// Save refresh token
export async function saveRefreshToken(token: string): Promise<void> {
  try {
    if (!token) {
      if (__DEV__) console.warn('⚠️ Attempted to save empty refresh token');
      return;
    }
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
    if (__DEV__) console.log('✅ Refresh token saved successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error saving refresh token (web):', error);
    throw error;
  }
}

// Get refresh token
export async function getRefreshToken(): Promise<string | null> {
  try {
    const token = localStorage.getItem(REFRESH_TOKEN_KEY);
    return token;
  } catch (error) {
    if (__DEV__) console.error('❌ Error getting refresh token (web):', error);
    return null;
  }
}

// Delete refresh token
export async function deleteRefreshToken(): Promise<void> {
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (__DEV__) console.log('✅ Refresh token deleted successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error deleting refresh token (web):', error);
    // Don't throw to prevent blocking logout
  }
}

// Save both tokens at once
export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  try {
    await Promise.all([
      saveToken(accessToken),
      saveRefreshToken(refreshToken)
    ]);
    if (__DEV__) console.log('✅ Both tokens saved successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error saving tokens (web):', error);
    throw error;
  }
}

// Delete both tokens (logout)
export async function clearAllTokens(): Promise<void> {
  try {
    await Promise.all([
      deleteToken(),
      deleteRefreshToken()
    ]);
    if (__DEV__) console.log('✅ All tokens cleared successfully (web)');
  } catch (error) {
    if (__DEV__) console.error('❌ Error clearing tokens (web):', error);
    // Don't throw to prevent blocking logout
  }
}

// Check if user is authenticated
export async function isAuthenticated(): Promise<boolean> {
  try {
    const token = await getToken();
    return !!token;
  } catch (error) {
    if (__DEV__) console.error('❌ Error checking authentication (web):', error);
    return false;
  }
}

// Get token info (for debugging)
export async function getTokenInfo(): Promise<{
  hasAccessToken: boolean;
  hasRefreshToken: boolean;
}> {
  try {
    const [accessToken, refreshToken] = await Promise.all([
      getToken(),
      getRefreshToken()
    ]);

    const info = {
      hasAccessToken: !!accessToken,
      hasRefreshToken: !!refreshToken
    };

    if (__DEV__) console.log('ℹ️ Token info (web):', info);
    return info;
  } catch (error) {
    if (__DEV__) console.error('❌ Error getting token info (web):', error);
    return { hasAccessToken: false, hasRefreshToken: false };
  }
}
