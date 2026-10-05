// Saves your Rhombus login for the tests, without automating the Google login.
// 1) Start Chrome yourself with a debugging port (see README), log in to Rhombus normally.
// 2) Run: npm run auth   -> this connects to that Chrome and saves .auth/state.json
import { chromium } from '@playwright/test';
import fs from 'fs';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = ctx.pages().find(p => p.url().includes('rhombusai.com')) ?? ctx.pages()[0];
console.log('Connected. Current page:', page?.url());
fs.mkdirSync('.auth', { recursive: true });
await ctx.storageState({ path: '.auth/state.json' });
const n = JSON.parse(fs.readFileSync('.auth/state.json', 'utf8')).cookies.filter(c => c.domain.includes('rhombus')).length;
console.log(`Saved .auth/state.json (${n} Rhombus cookies).`);
if (!n) console.log('WARNING: no Rhombus cookies found - make sure you are logged in to rhombusai.com in that Chrome window.');
await browser.close();
