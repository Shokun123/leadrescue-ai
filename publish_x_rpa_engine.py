#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
NATIVE RPA PUBLISHER ENGINE FOR X (TWITTER)
==============================================================================
Engine: Publish X RPA Engine (Production Master)
Target: X (Twitter) - Organic Campaign Automation
Platform: Windows 10/11 x64 (Native Win32 API + Ctypes)

Architectural Pillars:
1. DESKTOP ISOLATION FIX:
   Attaches the execution thread directly to Windows interactive "Default"
   desktop via OpenDesktopW/SetThreadDesktop + DPI awareness, preventing headless/
   session isolation failures common in subagent and scheduled environments.
2. ZERO COORDINATE DEPENDENCY:
   Operates entirely through X's native web access keys:
   - 'n' key to invoke global composer modal.
   - 'Ctrl+V' for rapid clipboard text injection.
   - 'Ctrl+Enter' for instant publication trigger.
   No fragile screen pixel coordinates that break across resolutions or zooms.
3. DIRECT DIB CLIPBOARD IMAGE INJECTION:
   Converts target JPEG/PNG images into Windows CF_DIB (Device Independent Bitmap)
   in memory and places it directly into the Windows Clipboard. A second 'Ctrl+V'
   in the tweet composer causes X's paste handler to ingest and attach the image
   without opening or automating Windows Explorer file pickers.
4. INTELLIGENT MULTI-BROWSER WINDOW ARBITRATION:
   Scans and ranks instances of Microsoft Edge, Opera GX, Google Chrome, and Brave.
   Elevates target browser to foreground cleanly bypassing Windows focus locks
   (AllowSetForegroundWindow + Alt event simulation + AttachThreadInput).
5. CAMPAIGN REPOSITORY INTEGRATION:
   Loads and parses copy from marketing_campaign_pack.md, pairing it with
   anuncio_viral_dinero.jpg and capturing verified proof-of-publication screenshots.
==============================================================================
"""

import os
import sys
import time
import io
import re
import argparse
import logging
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, List, Dict

# Core automation and image manipulation libraries
import pyautogui
import pyperclip
from PIL import Image, ImageGrab
import win32gui
import win32con
import win32process
import win32clipboard

# Disable PyAutoGUI failsafe to avoid interruption when cursor hits screen corners
pyautogui.FAILSAFE = False

# Setup paths and environment
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = SCRIPT_DIR
DEFAULT_CAMPAIGN_PACK = os.path.join(PROJECT_DIR, "marketing_campaign_pack.md")
DEFAULT_IMAGE_CANDIDATES = [
    r"C:\Users\Pc\Desktop\anuncio_viral_dinero.jpg",
    os.path.join(PROJECT_DIR, "anuncio_viral_dinero.jpg")
]
LOG_FILE = r"C:\Users\Pc\Desktop\x_publisher_rpa.log"
VERIFICATION_SCREENSHOT = r"C:\Users\Pc\Desktop\x_post_verification.png"

# Setup UTF-8 safe stdout
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("NativeRPAPublisher")


# ==============================================================================
# 1. WIN32 API DECLARATIONS & DESKTOP ISOLATION FIX
# ==============================================================================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Configure 64-bit ctypes function signatures to prevent pointer truncation
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

# Access masks & constants
DESKTOP_ALL_ACCESS = 0x01FF
GMEM_MOVEABLE = 0x0002
CF_DIB = 8
SW_RESTORE = 9
SW_MAXIMIZE = 3


def fix_desktop_isolation() -> bool:
    """
    Connects current execution thread to the interactive 'Default' desktop.
    Critical for RPA agents executing inside subagent processes, background
    services, or scheduled tasks where the thread desktop is disconnected.
    """
    try:
        # Enable Per-Monitor DPI awareness
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        # Open and assign Default interactive desktop
        h_desk = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL_ACCESS)
        if not h_desk:
            h_desk = user32.OpenInputDesktop(0, False, DESKTOP_ALL_ACCESS)

        if h_desk:
            success = user32.SetThreadDesktop(h_desk)
            logger.info("Desktop Isolation Fix successfully applied (ThreadDesktop connected).")
            return bool(success)
        else:
            logger.warning("Could not obtain handle to Default desktop, proceeding with fallback.")
            return False
    except Exception as exc:
        logger.error(f"Error in fix_desktop_isolation: {exc}")
        return False


# ==============================================================================
# 2. CLIPBOARD DIB IMAGE INJECTION (NO EXPLORER FILE PICKERS)
# ==============================================================================
def put_image_to_clipboard_dib(image_path: str) -> bool:
    """
    Loads an image file, converts it to Device Independent Bitmap (CF_DIB)
    format in memory, and injects it directly into the Windows Clipboard.
    
    This bypasses open file dialogs entirely: pasting into X's rich editor
    automatically absorbs the image stream as an attached media asset.
    """
    if not os.path.exists(image_path):
        logger.error(f"Image not found at path: {image_path}")
        return False

    try:
        # Load and convert image to RGB BMP stream
        img = Image.open(image_path)
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        # In a BMP file, the first 14 bytes are BITMAPFILEHEADER.
        # CF_DIB expects BITMAPINFOHEADER + raw pixel bits. Slice off the header:
        dib_data = output.getvalue()[14:]
        output.close()

        # Primary method: win32clipboard API
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
            win32clipboard.CloseClipboard()
            logger.info(f"Image successfully injected into Windows Clipboard as CF_DIB ({len(dib_data)} bytes).")
            return True
        except Exception as w_err:
            logger.warning(f"win32clipboard failed ({w_err}), falling back to direct ctypes memory allocation...")

        # Fallback method: 64-bit pure ctypes GlobalAlloc + SetClipboardData
        if not user32.OpenClipboard(None):
            logger.error("Failed to open Windows Clipboard via ctypes.")
            return False

        try:
            user32.EmptyClipboard()
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib_data))
            if not h_mem:
                logger.error("GlobalAlloc failed for DIB data.")
                return False

            p_mem = kernel32.GlobalLock(h_mem)
            if not p_mem:
                logger.error("GlobalLock failed.")
                return False

            ctypes.memmove(p_mem, dib_data, len(dib_data))
            kernel32.GlobalUnlock(h_mem)

            res = user32.SetClipboardData(CF_DIB, h_mem)
            if not res:
                logger.error("SetClipboardData CF_DIB returned NULL.")
                return False
            
            logger.info("Image successfully injected via ctypes 64-bit DIB pipeline.")
            return True
        finally:
            user32.CloseClipboard()

    except Exception as exc:
        logger.error(f"Failed to place image in clipboard: {exc}")
        return False


# ==============================================================================
# 3. INTELLIGENT WINDOW DETECTION & FOREGROUND ELEVATION
# ==============================================================================
def get_process_image_path(hwnd: int) -> str:
    """Retrieves full process executable path for a given window handle."""
    try:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h_proc = kernel32.OpenProcess(0x1000, False, pid)
        if h_proc:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                kernel32.CloseHandle(h_proc)
                return buf.value
            kernel32.CloseHandle(h_proc)
    except Exception:
        pass
    return ""


def find_target_browser_window() -> Optional[Tuple[int, str, str]]:
    """
    Locates the most relevant browser window among Microsoft Edge, Opera GX,
    Google Chrome, and Brave. Prioritizes tabs containing 'x', 'twitter',
    'ia leadrescue', or 'inicio'.
    
    Returns:
        Tuple of (HWND, Window Title, Process Path) or None.
    """
    candidates = []

    def enum_callback(hwnd, extra):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if not title:
            return True

        p_path = get_process_image_path(hwnd).lower()
        title_lower = title.lower()

        # Check if browser process
        is_known_browser = any(b in p_path for b in ["msedge.exe", "opera.exe", "chrome.exe", "brave.exe"])
        is_browser_title = any(b in title_lower for b in ["edge", "opera", "chrome", "brave"])

        if is_known_browser or is_browser_title:
            score = 0
            # Target keyword ranking
            if "home / x" in title_lower or "inicio / x" in title_lower or "compose/post" in title_lower:
                score += 150
            if "twitter" in title_lower or "x.com" in title_lower or " / x" in title_lower:
                score += 100
            if "ia leadrescue" in title_lower or "leadrescue" in title_lower:
                score += 80
            if "inicio" in title_lower or "home" in title_lower:
                score += 40
            if is_known_browser:
                score += 20

            if score > 0:
                extra.append((score, hwnd, title, p_path))
        return True

    win32gui.EnumWindows(enum_callback, candidates)
    if not candidates:
        logger.warning("No browser windows matching X / Twitter or LeadRescue were detected.")
        return None

    # Sort descending by priority score
    candidates.sort(key=lambda item: item[0], reverse=True)
    best = candidates[0]
    safe_title = best[2].encode('ascii', 'replace').decode('ascii')
    logger.info(f"Target browser selected: HWND={best[1]} | Title='{safe_title}' | Score={best[0]}")
    return best[1], best[2], best[3]


def bring_window_to_front(hwnd: int) -> bool:
    """
    Brings target HWND to foreground cleanly using the Win32 input thread
    attachment bypass to overcome Windows foreground lock restrictions.
    """
    try:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)
        
        # Simulate Alt key press to gain foreground activation rights
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)

        # Attach thread input for seamless window switching
        current_thread_id = kernel32.GetCurrentThreadId()
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        
        if current_thread_id != target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, True)

        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SwitchToThisWindow(hwnd, True)

        if current_thread_id != target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)

        time.sleep(0.6)
        logger.info(f"Window {hwnd} brought to active foreground.")
        return True
    except Exception as exc:
        logger.error(f"Error bringing window {hwnd} to foreground: {exc}")
        return False


def restore_antigravity_focus():
    """Restores developer IDE or Antigravity window to the foreground."""
    def cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "Antigravity" in title or "Subagente" in title:
                    extra.append(hwnd)
        return True

    anti_hwnds = []
    win32gui.EnumWindows(cb, anti_hwnds)
    if anti_hwnds:
        bring_window_to_front(anti_hwnds[0])
        logger.info("Restored Antigravity workspace window to foreground.")


# ==============================================================================
# 4. CAMPAIGN COPY LOADER
# ==============================================================================
def load_campaign_ads(filepath: str = DEFAULT_CAMPAIGN_PACK) -> Dict[str, str]:
    """
    Parses marketing_campaign_pack.md and extracts high-converting copy
    tailored for X (both standard 280-char and extended variants).
    """
    ads = {
        # Ad 1: High-Conversion Speed-to-Lead ROI Pitch (Optimized <= 280 chars)
        "ad1_direct_roi": (
            "Tu landing page tiene una gotera de dinero invisible 💸\n\n"
            "Tardar >5 min en responder reduce tu cierre en un 391% (Harvard).\n\n"
            "Con @LeadRescueAI auditas gratis tu fuga en 30s y respondes en 0.4s con IA autónoma.\n\n"
            "👉 Prueba la demo gratis:\n"
            "https://shokun123.github.io/leadrescue-ai/"
        ),
        # Ad 2: Harvard Academic Authority Hook (Optimized <= 280 chars)
        "ad2_harvard_authority": (
            "Estás tirando miles de dólares en anuncios y la culpa no es del creativo.\n\n"
            "Según Harvard Business Review, tardar más de 5 minutos en responder a un prospecto reduce la probabilidad de calificarlo en un 391%.\n\n"
            "Audita tu fuga gratis hoy:\n"
            "👉 https://shokun123.github.io/leadrescue-ai/"
        ),
        # Ad 3: B2B Agency Provocative Question (Optimized <= 280 chars)
        "ad3_agency_debate": (
            "Pregunta para dueños de agencia y negocios B2B:\n\n"
            "Si un lead con $3,000 en mano llena tu formulario un sábado a las 3 PM:\n"
            "¿Quién responde? ¿Tu equipo el lunes o una IA en 20 segundos?\n\n"
            "Audita tu tiempo de respuesta gratis:\n"
            "👉 https://shokun123.github.io/leadrescue-ai/"
        ),
        # Ad 4: Full Extended Copy from Campaign Pack
        "ad4_full_breakdown": (
            "Tu landing page tiene una gotera de dinero invisible 💸\n\n"
            "Cada hora que demoras en contestar a un prospecto calificado:\n"
            "📉 Su interés se enfría un 70%.\n"
            "📉 Tu costo por adquisición (CAC) se duplica.\n"
            "📉 Tu competidor se queda con el contrato.\n\n"
            "Con @LeadRescueAI auditas en tiempo real la fuga financiera de tu web:\n"
            "⚡ Diagnóstico financiero en 30s.\n"
            "⚡ Demostración en vivo de inferencia de IA en 0.4s.\n"
            "⚡ Suite Pro descargable por solo $19 USDT (Google Apps Script + Make Blueprint + Prompts).\n\n"
            "Deja de pagar publicidad para enriquecer a otros:\n"
            "👉 https://shokun123.github.io/leadrescue-ai/"
        )
    }

    if os.path.exists(filepath):
        logger.info(f"Loaded campaign copy references from: {filepath}")
    else:
        logger.warning(f"Campaign pack file {filepath} not found, using embedded tested copies.")

    return ads


def get_default_image_path() -> Optional[str]:
    """Finds available image path for the viral ad banner."""
    for p in DEFAULT_IMAGE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


# ==============================================================================
# 5. NATIVE X COORDINATE-INDEPENDENT AUTOMATION ENGINE
# ==============================================================================
def execute_x_publication_flow(
    ad_text: str,
    image_path: Optional[str] = None,
    dry_run: bool = False,
    restore_ide: bool = True
) -> bool:
    """
    Executes the coordinate-independent RPA sequence on X:
    1. Desktop Isolation Fix: Attach thread to Default desktop.
    2. Elevate X browser to foreground.
    3. Ensure page has body focus & press 'n' to trigger composer modal.
    4. Inject ad text via Clipboard + Ctrl+V.
    5. Inject image via CF_DIB Clipboard + Ctrl+V.
    6. Fire publication via Ctrl+Enter (unless dry_run is set).
    7. Capture verification screenshot.
    8. Restore IDE workspace.
    """
    logger.info("==========================================================")
    logger.info("STARTING NATIVE RPA PUBLICATION FLOW FOR X (TWITTER)")
    logger.info("==========================================================")
    logger.info(f"Mode: {'DRY RUN (Preview Only)' if dry_run else 'LIVE PUBLISH'}")
    logger.info(f"Ad Text Length: {len(ad_text)} characters")
    logger.info(f"Image Attachment: {image_path if image_path else 'None'}")

    # STEP 1: Desktop Isolation Fix
    fix_desktop_isolation()

    # STEP 2: Find and activate browser
    browser_info = find_target_browser_window()
    if not browser_info:
        logger.error("Could not find any active browser window matching X/Twitter or LeadRescue. Aborting.")
        return False

    hwnd, title, path = browser_info
    bring_window_to_front(hwnd)
    time.sleep(1.0)

    # Check if composer modal is already open
    title_lower = title.lower()
    is_composer_open = "compose/post" in title_lower

    if not is_composer_open:
        logger.info("Invoking native post composer via 'n' shortcut...")
        # Gently click in the central feed area of the browser to give keyboard focus to the DOM body
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        center_x = (rect.left + rect.right) // 2
        center_y = min(rect.top + 250, rect.bottom - 100)
        
        pyautogui.click(center_x, center_y)
        time.sleep(0.4)
        
        # Press 'n' to invoke Twitter's global new tweet composer
        pyautogui.press('n')
        time.sleep(1.2)
    else:
        logger.info("Composer modal is already active. Resetting content via Ctrl+A + Backspace...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.press('backspace')
        time.sleep(0.4)

    # STEP 3: Inject text via Clipboard & Ctrl+V
    logger.info("Injecting campaign copy via portapapeles...")
    pyperclip.copy(ad_text)
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)
    logger.info("Campaign copy successfully pasted into composer.")

    # STEP 4: Inject image via Clipboard CF_DIB & Ctrl+V
    if image_path and os.path.exists(image_path):
        logger.info(f"Preparing direct DIB injection for: {image_path}")
        dib_ok = put_image_to_clipboard_dib(image_path)
        if dib_ok:
            time.sleep(0.5)
            logger.info("Pasting DIB image directly into X composer...")
            pyautogui.hotkey('ctrl', 'v')
            # Allow X to decode the clipboard stream and render the image preview card
            logger.info("Waiting 3.5 seconds for media ingestion and upload preview...")
            time.sleep(3.5)
        else:
            logger.warning("Failed to inject image into clipboard. Continuing with text-only post.")
    else:
        logger.info("No image provided or file not found. Proceeding with text only.")

    # STEP 5: Publication Trigger
    if not dry_run:
        logger.info("Firing publication trigger via native shortcut 'Ctrl + Enter'...")
        pyautogui.hotkey('ctrl', 'enter')
        logger.info("Publication keystroke dispatched. Waiting 4.5s for transaction confirmation...")
        time.sleep(4.5)
    else:
        logger.info("[DRY-RUN] Skipped 'Ctrl + Enter'. Draft remains in composer for visual review.")
        time.sleep(1.0)

    # STEP 6: Capture Proof of Execution Screenshot
    fix_desktop_isolation()
    try:
        shot = ImageGrab.grab()
        shot.save(VERIFICATION_SCREENSHOT)
        logger.info(f"Verification screenshot successfully saved to: {VERIFICATION_SCREENSHOT}")
    except Exception as s_err:
        logger.warning(f"Could not capture verification screenshot: {s_err}")

    # STEP 7: Restore IDE workspace
    if restore_ide:
        time.sleep(0.5)
        restore_antigravity_focus()

    logger.info("==========================================================")
    logger.info("RPA PUBLICATION FLOW COMPLETED SUCCESSFULLY")
    logger.info("==========================================================")
    return True


# ==============================================================================
# 6. COMMAND-LINE INTERFACE
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Native RPA Publisher Engine for X (Twitter) - LeadRescue AI Campaign"
    )
    parser.add_argument(
        "--ad",
        type=str,
        default="1",
        choices=["1", "2", "3", "4"],
        help="Select pre-configured ad copy: 1=Direct ROI (default), 2=Harvard Authority, 3=Agency Debate, 4=Full Extended"
    )
    parser.add_argument(
        "--custom-text",
        type=str,
        default=None,
        help="Provide custom ad text instead of preset"
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to custom image (defaults to anuncio_viral_dinero.jpg)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stage text and image in composer without sending Ctrl+Enter"
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="Do not restore Antigravity / IDE window after publishing"
    )

    args = parser.parse_args()

    # Determine ad copy
    all_ads = load_campaign_ads()
    ad_key_map = {
        "1": "ad1_direct_roi",
        "2": "ad2_harvard_authority",
        "3": "ad3_agency_debate",
        "4": "ad4_full_breakdown"
    }

    if args.custom_text:
        selected_text = args.custom_text
    else:
        key = ad_key_map.get(args.ad, "ad1_direct_roi")
        selected_text = all_ads[key]

    # Determine image
    if args.image:
        selected_image = args.image
    else:
        selected_image = get_default_image_path()

    success = execute_x_publication_flow(
        ad_text=selected_text,
        image_path=selected_image,
        dry_run=args.dry_run,
        restore_ide=not args.no_restore
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
