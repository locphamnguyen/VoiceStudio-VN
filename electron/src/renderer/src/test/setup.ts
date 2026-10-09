import '@testing-library/jest-dom/vitest';

// VoiceStudio-VN mở giao diện bằng tiếng Việt khi chưa ai chọn ngôn ngữ. Bộ
// test viết theo chuỗi tiếng Anh, nên ghim tiếng Anh trước khi i18n khởi tạo.
try {
  if (!localStorage.getItem('voicestudio.locale')) localStorage.setItem('voicestudio.locale', 'en');
} catch {
  // jsdom luôn có localStorage; phòng môi trường bị chặn lưu trữ.
}
