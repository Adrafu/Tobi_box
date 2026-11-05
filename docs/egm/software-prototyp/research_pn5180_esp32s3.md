# Research: PN5180 + ESP32-S3 SuperMini (Tonie / SLIX-L / HID+CDC)

Scope: read-only research. Sources were cloned to
`/tmp/claude-0/-home-user-Tobi-box/87837eca-ee4b-54f9-bcf7-9cb39d3c88c0/scratchpad/ext/` (pn5180lib, espuino, arduino-esp32).
Tags: **[src]** = verified in cloned source (file:line given), **[web]** = verified in a web source (secondary, snippet level), **[unv]** = unverified.

---

## 1. tueddy PN5180 library

- **Correct repo: https://github.com/tueddy/PN5180-Library** (the URL `tueddy/PN5180` in the brief failed to clone). [src]
- HEAD of clone: `69ec032289457b1adae3e1b269ca22ea16aa46fd` (2025-09-01, "ISO14443: Explicitly allow unknown manufacturer ID 0xFF"). [src]
- Version: `library.properties` says `2.2.0` but the README release notes go up to **2.3.7**. Pin by commit, not by version. [src]
- PlatformIO `lib_deps` (commit-pinned):
  `https://github.com/tueddy/PN5180-Library.git#69ec032289457b1adae3e1b269ca22ea16aa46fd`
  ESPuino itself uses a fork (`biologist79/PN5180-Library.git#2479510696c8...`, reduced RF timeouts 500/200 ms -> 100 ms to avoid false "card removed"). Look at `espuino/platformio.ini:48`. [src]
- Arduino IDE: install as zip from the GitHub repo (Sketch > Include Library > Add .ZIP). Library Manager entry not verified. [unv]

### Public API (all verified in `PN5180.h`, `PN5180ISO14443.h`, `PN5180ISO15693.h`)

Constructors / setup:
- `PN5180(uint8_t SSpin, uint8_t BUSYpin, uint8_t RSTpin, SPIClass& spi=SPI)` (PN5180.h:101)
- `PN5180ISO14443(uint8_t SSpin, uint8_t BUSYpin, uint8_t RSTpin, SPIClass& spi=SPI)` (PN5180ISO14443.h:28)
- `PN5180ISO15693(uint8_t SSpin, uint8_t BUSYpin, uint8_t RSTpin, SPIClass& spi=SPI)` (PN5180ISO15693.h:42)
- `void begin(int8_t sck=-1, int8_t miso=-1, int8_t mosi=-1, int8_t SSpin=-1)` (PN5180.h:104; pins are optional, default SPI used if -1)
- `void end()`, `void setSPISettingsFrecuency(uint32_t)` (sic, spelling in lib). Default SPI clock 7 MHz, MODE0 (PN5180.cpp:59).

Reset / RF:
- `void reset()` (PN5180.h:152), hard reset via RST pin.
- `bool setRF_on()`, `bool setRF_off()` (PN5180.h:142/144)
- `bool loadRFConfig(uint8_t txConf, uint8_t rxConf)` (PN5180.h:139)
- `bool setupRF()` on the protocol classes: 14443 (PN5180ISO14443.h:43), 15693 (PN5180ISO15693.h:68). 15693 uses `loadRFConfig(0x0d, 0x8d)` (PN5180ISO15693.cpp:816).

ISO14443A (NTAG215 UID):
- `int8_t activateTypeA(uint8_t *buffer, uint8_t kind)` (PN5180ISO14443.h:35). `kind`: 0 = REQA, 1 = WUPA (ESPuino uses WUPA to re-read halted cards).
- `int8_t readCardSerial(uint8_t *buffer)` (PN5180ISO14443.h:44); hardcodes REQA. Returns UID length, <=0 on miss.
- `bool isCardPresent()` (PN5180ISO14443.h:45).
- `bool mifareHalt()` (PN5180ISO14443.h:38).
- `bool mifareBlockRead(uint8_t blockno, uint8_t *buffer)` (PN5180ISO14443.h:36).
- Public member `uint16_t commandTimeout = 500;` (PN5180.h:154). ESPuino sets 100 ms.

ISO15693 (inventory / SLIX-L privacy):
- `ISO15693ErrorCode getInventory(uint8_t *uid)` (PN5180ISO15693.h:48). UID is 8 bytes. Sends `26 01 00` (PN5180ISO15693.cpp:38).
- `ISO15693ErrorCode getInventoryMultiple(uint8_t *uid, uint8_t maxTags, uint8_t *numCard)` (h:49)
- `ISO15693ErrorCode inventoryPoll(uint8_t *uid, uint8_t maxTags, uint8_t *numCard, uint8_t *numCol, uint16_t *collision)` (h:46)
- `ISO15693ErrorCode readSingleBlock(const uint8_t *uid, uint8_t blockNo, uint8_t *blockData, uint8_t blockSize)` (h:51)
- `ISO15693ErrorCode getSystemInfo(uint8_t *uid, uint8_t *blockSize, uint8_t *numBlocks)` (h:55)
- `ISO15693ErrorCode getRandomNumber(uint8_t *randomData)` (h:58). Sends `02 B2 04` (cpp:603).
- `ISO15693ErrorCode setPassword(uint8_t identifier, const uint8_t *password, const uint8_t *random)` (h:59). Sends `02 B3 04 <id> ...`, XORs password with random (cpp:618).
- `ISO15693ErrorCode enablePrivacy(const uint8_t *password, const uint8_t *random)` (h:60). Sends `02 BA 04 ...` (cpp:634).
- `ISO15693ErrorCode enablePrivacyMode(const uint8_t *password)` (h:62): GET RANDOM, then ENABLE PRIVACY (cpp:660).
- `ISO15693ErrorCode disablePrivacyMode(const uint8_t *password)` (h:63): GET RANDOM, then `setPassword(0x04, password, random)` (cpp:646-657). **Unlock = identifier 0x04 (privacy password).**
- `const char *strerror(ISO15693ErrorCode)` (h:69). Error enum at h:26-36 (`ISO15693_EC_OK = 0`).
- Library README: privacy commands are documented for **ICODE SLIX2 (SL2S2602)**. [src]

**Not found in library:** a dedicated LPCD-based card-presence API for ISO15693, a `getUID` alias, or any "removed" event. Removal must be inferred by the caller.

LPCD (verified in source, PN5180.h:51-59, 133-135):
- `bool prepareLPCD()` (PN5180.h:133)
- `bool switchToLPCD(uint16_t wakeupCounterInMs)` (PN5180.h:135). Valid range per ESPuino comment 0x0-0xA82 (about 2960 ms max).
- EEPROM config constants: `LPCD_THRESHOLD` (0x37), `LPCD_FIELD_ON_TIME` (0x36), `LPCD_REFERENCE_VALUE` (0x34). Set via `writeEEprom`.
- ESPuino notes LPCD needs PN5180 firmware **>= 4.0**. Read via `readEEprom(FIRMWARE_VERSION, ...)`. [src: espuino/src/RfidPn5180.cpp:565-570]

Other: `bool writeRegister`, `readRegister`, `sendData`, `readData`, `getIRQStatus()`, `clearIRQStatus(uint32_t)` (PN5180.h:113-156).

---

## 2. How ESPuino uses the PN5180

Source: `espuino/src/RfidPn5180.cpp` (ESPuino clone, default branch). Key facts:

**Polling loop** (cpp:241-268):
- Single FreeRTOS task, `vTaskDelay(10 ms)` per loop (cpp:269).
- Round robin: `RESET14443 -> READCARD -> RESET15693 -> SETUPRF -> GETINVENTORY -> DISABLEPRIVACYMODE -> GETINVENTORY_PRIVACY` (state numbers 1..7, cpp:28-39 and 530-533).
- While a card is active, it skips the reset and polls directly (cpp:516-528). The comment says a hardware reset per poll collapses the RF field.

**Removal detection** (no explicit "removed" event; it is a debounce timeout, cpp:343-366):
```
if (!lastTimeDetected14443 || (millis() - lastTimeDetected14443 >= debounceMs)) {
    if (lastTimeDetected14443) { /* silent re-init sweep, then re-check */ ... continue; }
    lastTimeDetected14443 = 0; cardAppliedCurrentRun = false; /* clear lastCardId */
} else { stateMachine = ACTIVE; }   // still "present" within the debounce window
```
- `debounceMs = gPrefsRfid.getUShort("pn5180Debounce", 500)` (cpp:246). Default 500 ms.
- **Wedge vs removal:** before declaring removal, ESPuino runs one "silent re-init" sweep (cpp:41-51 comment, 345-357). If the card is re-found, it continues silently. Only if the sweep finds nothing is it a removal.
- Removal pause: `if (!cardAppliedCurrentRun && cardAppliedLastRun && ...) AudioPlayer_SetTrackControl(PAUSEPLAY)` (cpp:444-452), gated by `gPlayProperties.pauseIfRfidRemoved`.

**Same-card / re-apply handling** (cpp:460-471, 481-513): compares UID with `lastCardId` and `lastValidcardId`, so the same card on the reader does not re-queue.

**Read function** (cpp:194-239): `activateTypeA(response, 1)` = WUPA, then `mifareHalt()` after each read so the card can be woken again. UID validity checks (0xFF/0x88 filters).

**Privacy handling (SLIX2/SLIX-L Tonie)** (cpp:370-387):
- Password is a 4-byte value, default `{0x0F,0x0F,0x0F,0x0F}` (RfidPn5180.h:11-13, [src]).
- Stored in NVS key `"slixPwd"` (RfidPn5180.h:9); overridden at task start if a 4-byte value exists (cpp:247-250). Set via the web UI (Web.cpp:838).
- In state DISABLEPRIVACYMODE: `disablePrivacyMode(currentSlixPrivacyPassword.data())` (cpp:378). Password snapshot is taken each time, so a web-UI change applies immediately.
- Flow: if the call returns OK, it logs "disabling privacy-mode successful" once. On the next OK it advances to GETINVENTORY_PRIVACY. Failure falls through to the normal state++ path. Effectively: unlock on each poll, then read the inventory in the next state.
- Notes: the `enablePrivacyMode` function is not used by ESPuino. ESPuino only unlocks.

**LPCD**: used only for **deep-sleep wakeup**, not for live polling (cpp:100-175, 553-596). It is enabled by pref `pn5180Lpcd` (default false). Wakeup on IRQ pin via EXT1. The IRQ pin is GPIO39 on LOLIN D32 Pro.

**Reader reset** (cpp:286-293): `begin()`, `reset()`, `commandTimeout = 100`, reads firmware version. Note: ESPuino does NOT call `setupRF()` on the 14443 path at init; it uses `setupRF()` only in state SETUPRF for 15693 (cpp:372-373). [src]

---

## 3. PN5180 module wiring and power

ESPuino pin map (LOLIN D32 Pro, `espuino/src/settings-lolin_d32_pro.h:37-45`) [src]:

| Signal | GPIO | Notes |
|---|---|---|
| NSS (CS) | 21 | `RFID_CS` |
| MOSI | 13 | |
| MISO | 15 | |
| SCK | 14 | |
| BUSY | 33 | required by library |
| RST | 22 | required by library |
| IRQ | 39 | only for LPCD wakeup; optional |

Library SPI init: `begin(sck, miso, mosi, ss)` (PN5180.cpp:69-81). Sets NSS/RST outputs and BUSY input.

ESP32-S3 default SPI (arduino variant `variants/esp32s3/pins_arduino.h:28-31`) [src]: SS=10, MOSI=11, MISO=13, SCK=12. Use these or pass explicit pins to `begin()`.

Voltages (PN5180 datasheet, **[web] only**; the NXP PDF is binary and was not parseable):
- VBAT (main): 2.7 / 3.3 typ / 5.5 V max.
- TVDD (TX driver): 2.7 / 5.0 typ / 5.5 V max. This is the RF output stage.
- PVDD (digital IO): rail-dependent, 1.65-1.95 V (1.8 V rail) or 2.7-3.6 V (3.3 V rail).
- Source: search snippets of PN5180A0XX_C3_C4 datasheet (2025). Check the PDF before finalising. [web/unv]
- Practical: the **digital IO (SPI, BUSY, RST, IRQ)** is a 3.3 V domain on the ESP32-S3. The TX driver (TVDD) is 5 V typ. Many cheap modules have an on-board LDO fed from 5 V. [unv for module specifics]
- "VDDPA" is **not** a datasheet pin name in the snippets. [web]

ESP32-S3 pin constraints:
- Avoid GPIO19/20 (native USB D-/D+ on SuperMini). The arduino variant maps them to A18/A19 (`pins_arduino.h:51-52`). [src for mapping; USB role unv]
- Strapping pins (GPIO0, 3, 45, 46) and octal-PSRAM pins [unv for this board] should be avoided.
- SuperMini (espboards.dev): 4 MB flash, PSRAM is only on the R2 variant. [web]

---

## 4. ESP32-S3 USB: HID keyboard + CDC serial (arduino-esp32 v3.x)

Source: `arduino-esp32` master clone, commit `a6934e850667a02d2bf4b1166d69773e0230eab9`. [src]

**Two USB peripherals on the S3:**
- `ARDUINO_USB_MODE = 1`: "hardware" USB Serial/JTAG CDC. This is the built-in JTAG/CDC controller. **No HID.** (USBCDC.h:136, HWCDC.h:110, HardwareSerial.h:442-443.)
- `ARDUINO_USB_MODE = 0`: USB-OTG via TinyUSB. This is the mode for HID and composite devices. (CompositeDevice example guards on this, see below.)

**Composite HID + CDC is feasible in OTG mode. Verified.** `libraries/USB/examples/CompositeDevice/CompositeDevice.ino`:
- `#elif ARDUINO_USB_MODE == 1` -> `#warning This sketch should be used when USB is in OTG mode` (line 4-7).
- `#if !ARDUINO_USB_CDC_ON_BOOT  USBCDC USBSerial;  #endif` (line 22-24). So CDC is declared explicitly when CDC-on-boot is off.
- `USBHIDKeyboard Keyboard;` (line 27), `USBSerial.begin()`, `Keyboard.begin()`, `USB.begin()` in `setup()` (lines ~140-150).
- Also `ci.yml` requires `CONFIG_SOC_USB_OTG_SUPPORTED=y`.

**Serial routing** (HardwareSerial.h:438-452) [src]:
- If `ARDUINO_USB_CDC_ON_BOOT=0`, `Serial` is `Serial0` (UART0). The S3 SuperMini has no UART bridge, so `Serial` output goes nowhere on the USB port. Use `USBSerial` for logs in this mode.
- If `ARDUINO_USB_CDC_ON_BOOT=1` and `ARDUINO_USB_MODE=1`, `Serial` = HWCDC.

**Recommended build flags for HID + CDC (OTG):**
```
-DARDUINO_USB_MODE=0
-DARDUINO_USB_CDC_ON_BOOT=0
```
Not verified whether the `esp32-s3-devkitc-1` board manifest already sets these. Set them explicitly. [unv for default]

**Arduino IDE equivalent:** Tools > USB Mode = "USB-OTG (TinyUSB)" and USB CDC On Boot = "Disabled". [web/unv; the menu names are from the IDE, not verified against the cloned boards.txt]

**Default USB identity (USB.cpp:25-45) [src]:** VID `0x303A` (Espressif), PID `0x0002`, product string = `ARDUINO_BOARD`. Set `USB.VID(...)`, `USB.PID(...)` (USB.h:53-57) to a unique PID so udev rules can match. Do not reuse 0x303A/0x0002 for a product.

**API (verified):**
- `USBHIDKeyboard::begin(const uint8_t *layout)` (USBHIDKeyboard.cpp:49) sets `_asciimap = layout`; the constructor defaults to `KeyboardLayout_en_US` (cpp:35). Layouts available: `KeyboardLayout_de_DE`, `en_US`, `fr_CH`, `es_ES`, etc. (USBHIDKeyboard.h:54-63).
- `write(uint8_t c)`, `press(uint8_t)`, `release(uint8_t)`, `pressRaw(uint8_t)`, `releaseRaw(uint8_t)`, `sendReport(KeyReport*)` (USBHIDKeyboard.cpp:85-219).
- `HID.ready()` (CompositeDevice example line ~83).

**Pitfalls** [unv unless noted]:
- Flashing: in OTG mode the USB port is the TinyUSB device. You may need BOOT+RST to enter download mode for upload. Confirm on the board. [unv]
- A single VID/PID means both HID and CDC share one device identity. Linux uses one `idVendor:idProduct` for both (see section 6).

---

## 5. HID keyboard on Linux with German layout

Verified facts from source (`arduino-esp32/libraries/USB/src/keyboardLayout/`):

- HID usage codes identify **physical key positions** (US layout labels). The library's default is `KeyboardLayout_en_US`.
- `en_US` table: `'y'` = `0x1C`, `'z'` = `0x1D`, `'a'`-`'f'` = `0x04`-`0x09`, `'0'` = `0x27`, `'1'`-`'9'` = `0x1E`-`0x26`. (KeyboardLayout_en_US.cpp, lines for 'y'/'z'.)
- `de_DE` table: `'y'` = `0x1D`, `'z'` = `0x1C`. Same a-f and digits. (KeyboardLayout_de_DE.cpp.)
- Consequence: if the ESP sends the **en_US** table and the host is German, a 'z' comes out as 'y' and vice versa. The same applies to uppercase Y/Z. (Consistent with the search snippet on QWERTZ/Y-Z swaps, [web].)
- **Hex digits 0-9 and a-f are safe on both layouts.** Digits (0x1E-0x27) and letters a-f (0x04-0x09) map to the same keycodes on US and DE. Shifted A-F (0x04/0x09 | SHIFT) are also identical. [src]
- Recommendation: either (a) keep en_US and only send 0-9a-f, or (b) call `Keyboard.begin(KeyboardLayout_de_DE)` if any y/z must be typed.
- Host side: Linux X11/Wayland layout must be German if you rely on the de_DE table. Otherwise the characters follow the host's keymap, which is what you want for a hex code.

---

## 6. Raspberry Pi device paths

Mostly **[unv]** (standard Linux behaviour, not verified in the sources here; the search only gave secondary forum posts):

- HID keyboard: appears as an evdev node `/dev/input/eventN`. Stable name: `/dev/input/by-id/usb-<vendor>_<product>-event-kbd` (plus `-if00-event-kbd` on composite devices). The `by-id` name uses vendor/product/serial strings.
- CDC serial: appears as `/dev/ttyACM0` (cdc_acm driver). Stable name: `/dev/serial/by-id/usb-<manufacturer>_<product>_<serial>-if00`.
- Composite device: one physical device, two interfaces. Both appear. The keyboard interface is usually `-if00`, CDC is `-if01` or `-if02`. Check with `udevadm info -q all -n /dev/input/eventN`.
- Custom udev rule example (match VID/PID and make a stable link):
  ```
  SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="yyyy", SYMLINK+="pn5180_ctl"
  SUBSYSTEM=="input", ATTRS{idVendor}=="xxxx", ATTRS{idProduct}=="yyyy", ENV{ID_INPUT_KEYBOARD}=="1", SYMLINK+="input/tonie_kbd"
  ```
  then `sudo udevadm control --reload && sudo udevadm trigger`. Syntax is standard udev, not verified on this Pi.
- Use `udevadm info -a -n /dev/ttyACM0` to find the VID/PID attributes you need.

---

## 7. SLIX-L caveat (important)

- ESPuino and the tueddy library are written for **ICODE SLIX2 (SL2S2602)**. Commands `B2`/`B3`/`BA` and the password XOR scheme are verified in source for that chip. [src]
- The user's tags are **SLIX-L (SL2S2002)**. Whether the same opcodes and password scheme apply is **unverified**. The NXP datasheet command section was not accessible. [unv]
- An NXP community thread reports intermittent failures when setting the privacy password on SLIX-L and says adding a delay between commands helped. [web]
- SLIX-L is said to have three passwords (privacy, destroy, EAS/AFI). [web]
- Action: test `getRandomNumber` + `disablePrivacyMode(0x0F0F0F0F)` on a real tag with the existing sketch before relying on it. Use the SL2S2002 datasheet command table to confirm opcodes. [unv]

---

## 8. Open items

1. Read the PN5180 datasheet (text version) for VBAT/TVDD/PVDD limits and the required module supply. [unv]
2. Confirm SLIX-L opcodes against the SL2S2002 datasheet. [unv]
3. Check whether the `esp32-s3-devkitc-1` board manifest sets `ARDUINO_USB_MODE`/`CDC_ON_BOOT` by default. [unv]
4. Confirm arduino-esp32 composite works on this SuperMini in PlatformIO (build with `-DARDUINO_USB_MODE=0 -DARDUINO_USB_CDC_ON_BOOT=0`). [unv]
