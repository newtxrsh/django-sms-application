// Live character + SMS segment counter for the message box.
//
// SMS rules:
// - GSM-7 (plain English letters, digits, common symbols): 160 characters fit
//   in one SMS. Longer messages are split into parts of 153 (7 are used to
//   join the parts back together).
// - Characters such as ^ { } [ ] ~ | \ and € are GSM-7 "extended" characters
//   and take up 2 places each.
// - Any other character (emoji, curly quotes, most accented letters except
//   ñ/é/ü/...) switches the whole message to Unicode: 70 per SMS, 67 per part.
(function () {
  'use strict';

  const GSM_BASIC = new Set(
    '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡' +
    'ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'
  );
  const GSM_EXTENDED = new Set('^{}\\[]~|€\f');

  function analyze(text) {
    let septets = 0;
    let isGsm = true;
    for (const ch of text) {
      if (GSM_BASIC.has(ch)) {
        septets += 1;
      } else if (GSM_EXTENDED.has(ch)) {
        septets += 2;
      } else {
        isGsm = false;
        break;
      }
    }
    // Unicode SMS are measured in UTF-16 units, so an emoji counts as 2.
    const units = isGsm ? septets : text.length;
    const single = isGsm ? 160 : 70;
    const multi = isGsm ? 153 : 67;
    let segments = 0;
    if (units > 0) {
      segments = units <= single ? 1 : Math.ceil(units / multi);
    }
    const capacity = segments <= 1 ? single : segments * multi;
    return { isGsm, segments, remaining: capacity - units };
  }

  const textarea = document.getElementById('id_message');
  const charCount = document.getElementById('char-count');
  const segmentCount = document.getElementById('segment-count');
  const encodingNote = document.getElementById('encoding-note');
  if (!textarea) {
    return;
  }
  const maxLength = parseInt(textarea.getAttribute('maxlength'), 10) || 1600;

  function update() {
    const text = textarea.value;
    // Count characters the same way Python's len() does (an emoji = 1).
    const length = Array.from(text).length;
    const info = analyze(text);

    charCount.textContent = `${length} / ${maxLength} characters`;
    charCount.classList.toggle('text-danger', length > maxLength);
    charCount.classList.toggle('fw-semibold', length > maxLength);

    const plural = info.segments === 1 ? '' : 's';
    segmentCount.textContent = info.segments === 0
      ? '0 SMS segments'
      : `${info.segments} SMS segment${plural} · ${info.remaining} left in this segment · ${info.isGsm ? 'GSM-7' : 'Unicode'}`;
    encodingNote.classList.toggle('d-none', info.isGsm);
  }

  textarea.addEventListener('input', update);
  update();

  // Prevent double-sending: disable the button and show a spinner while submitting.
  const form = document.getElementById('sms-form');
  const button = document.getElementById('send-button');
  form.addEventListener('submit', function () {
    button.disabled = true;
    button.querySelector('.spinner-border').classList.remove('d-none');
  });
  // Re-enable the button if the user comes back with the browser's Back button.
  window.addEventListener('pageshow', function () {
    button.disabled = false;
    button.querySelector('.spinner-border').classList.add('d-none');
  });
})();
