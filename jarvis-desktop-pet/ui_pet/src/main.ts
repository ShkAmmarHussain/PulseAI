import { listen } from '@tauri-apps/api/event';
import { appWindow } from '@tauri-apps/api/window';

async function init() {
  await listen('pet_state', (e) => {
    const s = e.payload;
    // update pet state later
  });
}
init();
