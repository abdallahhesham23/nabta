import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';

// Public values: the publishable key only grants what row-level security allows.
const SUPABASE_URL = 'https://iumdwrwagaawoyurvniu.supabase.co';
const SUPABASE_KEY = 'sb_publishable_jGcQYYOBSta47mCKtykSGQ_dSOU3kvZ';

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { storage: AsyncStorage, autoRefreshToken: true, persistSession: true, detectSessionInUrl: false },
});
