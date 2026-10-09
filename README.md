<div align="center">
  <img src="docs/logo.png" alt="VoiceStudio" width="88" />
  <h1>VoiceStudio — bản tiếng Việt</h1>
  <p><strong>Nhân bản giọng nói, thiết kế giọng, lồng tiếng video, chép lời và làm sách nói bằng AI — chạy ngay trên máy tính của bạn, giao diện 100% tiếng Việt.</strong></p>
  <p>
    <a href="#-cài-đặt-trên-windows">Cài trên Windows</a> ·
    <a href="#-cài-đặt-trên-macos">Cài trên macOS</a> ·
    <a href="#-cài-đặt-trên-linux">Cài trên Linux</a> ·
    <a href="#-đăng-ký-đăng-nhập-và-quản-lý-thành-viên">Đăng nhập</a> ·
    <a href="#-xử-lý-sự-cố">Xử lý sự cố</a> ·
    <a href="README_EN.md">English</a>
  </p>
</div>

![VoiceStudio: nhân bản giọng, thiết kế giọng, lồng tiếng và quản lý model](docs/media/electron/voicestudio.gif)

> **Đây là bản viết lại từ [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio)** (giấy phép AGPL-3.0) để **người không rành kỹ thuật cũng cài và dùng được**. Lõi xử lý giọng nói giữ nguyên bản gốc; phần thay đổi nằm ở cách cài, ngôn ngữ giao diện và lớp tài khoản người dùng — xem [Khác gì so với bản gốc](#-khác-gì-so-với-bản-gốc).

**Mục lục**: [Tính năng](#-tính-năng) · [Yêu cầu máy](#-yêu-cầu-máy) · [Windows](#-cài-đặt-trên-windows) · [macOS](#-cài-đặt-trên-macos) · [Linux](#-cài-đặt-trên-linux) · [Lần đầu sử dụng](#-lần-đầu-sử-dụng) · [Đăng nhập & thành viên](#-đăng-ký-đăng-nhập-và-quản-lý-thành-viên) · [Dùng chung trong mạng nội bộ](#-cho-nhiều-người-dùng-chung-trong-mạng-nội-bộ) · [Thông báo cập nhật](#-thông-báo-cập-nhật-và-gọi-về-trang-trung-tâm) · [Cấu hình nâng cao](#-cấu-hình-nâng-cao-tệp-env) · [Cập nhật](#-cập-nhật-lên-bản-mới) · [Gỡ cài đặt](#-gỡ-cài-đặt) · [Xử lý sự cố](#-xử-lý-sự-cố) · [Khác gì bản gốc](#-khác-gì-so-với-bản-gốc) · [Bản quyền](#-bản-quyền-và-sử-dụng-có-trách-nhiệm)

---

## ✨ Tính năng

| Tạo giọng | Sản xuất | Kết nối |
| :--- | :--- | :--- |
| Nhân bản giọng từ vài giây âm thanh mẫu | Lồng tiếng video, khớp thời gian từng câu | API cục bộ + MCP cho phần mềm khác |
| Thiết kế giọng từ mô tả (giới tính, tuổi, chất giọng…) | Truyện, sách nói, xử lý hàng loạt | Máy phụ (worker) chạy từ xa — tuỳ chọn |
| Đọc chính tả bằng giọng nói, chép lời ra phụ đề | Hội thoại nhiều giọng | **Tài khoản người dùng, duyệt thành viên** |

- Hơn **600 ngôn ngữ**, có **tiếng Việt**. Model mặc định là **VoiceStudio** (default, powered by k2-fsa/OmniVoice); có thể chọn thêm model khác ngay trong ứng dụng. Xem [danh mục tính năng & model](docs/feature-catalog.md).
- **Giọng nói và dữ liệu xử lý ngay trên máy bạn** — không gửi âm thanh, văn bản hay tài khoản lên mạng, không cần API key. Chỉ tải model từ Hugging Face khi bạn đồng ý. Thứ duy nhất tự gửi đi là **mã bản cài + số phiên bản** để nhận thông báo cập nhật — xem [Thông báo cập nhật](#-thông-báo-cập-nhật-và-gọi-về-trang-trung-tâm).
- **Giao diện tiếng Việt** ngay lần mở đầu tiên (vẫn đổi được sang 20 ngôn ngữ khác trong *Cài đặt*).

<details>
<summary><strong>Xem ảnh các màn hình</strong></summary>

<table>
  <tr>
    <td><img src="docs/media/electron/voice-cloning.png" alt="Nhân bản giọng" width="100%" /></td>
    <td><img src="docs/media/electron/dubbing.png" alt="Lồng tiếng video" width="100%" /></td>
  </tr>
  <tr><td align="center">Nhân bản giọng</td><td align="center">Lồng tiếng video</td></tr>
  <tr>
    <td><img src="docs/media/electron/voice-design.png" alt="Thiết kế giọng" width="100%" /></td>
    <td><img src="docs/media/electron/models.png" alt="Quản lý model" width="100%" /></td>
  </tr>
  <tr><td align="center">Thiết kế giọng</td><td align="center">Quản lý model</td></tr>
</table>

</details>

---

## 💻 Yêu cầu máy

| Hạng mục | Tối thiểu | Khuyến nghị |
|---|---|---|
| Hệ điều hành | Windows 10/11 (64-bit), macOS 13+, Linux 64-bit | Windows 11, macOS 14+, Ubuntu 22.04+ |
| Phần cứng | Chạy được bằng CPU nhưng **chậm** | Card **NVIDIA** ≥ 8 GB VRAM, hoặc MacBook chip **M1/M2/M3/M4** |
| RAM | 8 GB | 16 GB trở lên |
| Ổ đĩa trống | ~15 GB (thư viện + model) | 30 GB |
| Mạng | Cần Internet ở **lần cài đầu tiên** và lần đầu tải model | |

- Có card NVIDIA: chỉ cần **cập nhật driver NVIDIA mới nhất** (không phải cài CUDA Toolkit). Bộ cài tự nhận card và chọn bản PyTorch GPU.
- Mac chip Intel chỉ chạy được bằng CPU (rất chậm).

---

## 🪟 Cài đặt trên Windows

Chỉ có **3 bước**, không phải gõ lệnh.

**Bước 1 — Tải mã nguồn về máy**

- Cách dễ nhất: trên trang GitHub của dự án bấm nút xanh **Code → Download ZIP**, rồi **giải nén** vào một thư mục ngắn, **không dấu, không dấu cách**, ví dụ `C:\VoiceStudio`.
- Hoặc nếu đã có Git: mở PowerShell rồi gõ
  ```powershell
  git clone https://github.com/locphamnguyen/VoiceStudio-VN.git C:\VoiceStudio
  ```

> ⚠️ Đừng để thư mục trong `Downloads\Thư mục có dấu\...` hay đường dẫn quá dài — Python trên Windows hay lỗi với đường dẫn có dấu tiếng Việt.

**Bước 2 — Bấm đúp `CaiDat-Windows.cmd`**

Một cửa sổ đen hiện ra và tự làm hết mọi việc:

1. Cài **uv** (quản lý Python) và **bun** (build giao diện) nếu máy chưa có.
2. Cài Python + toàn bộ thư viện, **tự chọn bản GPU** nếu có card NVIDIA.
3. Build giao diện web.
4. Tạo lối tắt **VoiceStudio** ngoài Desktop.

Lần đầu mất khoảng **10–30 phút** tuỳ tốc độ mạng — cứ để máy chạy, khi thấy dòng chữ xanh **"CÀI ĐẶT XONG!"** là xong.

> Nếu Windows hiện cảnh báo *"Windows protected your PC"*, bấm **More info → Run anyway**. Đây là tệp script trong chính thư mục bạn vừa tải.

**Bước 3 — Mở VoiceStudio**

Bấm đúp lối tắt **VoiceStudio** ngoài Desktop (hoặc tệp `ChayVoiceStudio-Windows.cmd`). Khoảng 20–60 giây sau trình duyệt tự mở trang <http://localhost:3900>.

- **Đừng đóng cửa sổ đen** trong lúc dùng — đóng nó là tắt VoiceStudio.
- Tiếp theo: xem [Lần đầu sử dụng](#-lần-đầu-sử-dụng).

---

## 🍎 Cài đặt trên macOS

**Bước 1 — Tải mã nguồn**: bấm **Code → Download ZIP** trên trang GitHub, giải nén vào thư mục *Home* (ví dụ `/Users/<tên-bạn>/VoiceStudio`). Hoặc mở **Terminal**:

```bash
git clone https://github.com/locphamnguyen/VoiceStudio-VN.git ~/VoiceStudio
```

**Bước 2 — Cài đặt**: bấm đúp tệp **`CaiDat-Mac.command`**.

- Nếu macOS báo *"không thể mở vì từ nhà phát triển không xác định"*: **chuột phải → Open → Open**.
- Nếu máy chưa có *Command Line Tools*, một hộp thoại cài đặt sẽ hiện ra — bấm **Cài đặt**, chờ xong rồi bấm đúp `CaiDat-Mac.command` lần nữa.
- Nếu bấm đúp không có tác dụng, mở Terminal và gõ: `cd ~/VoiceStudio && ./cai-dat.sh`

**Bước 3 — Mở VoiceStudio**: bấm đúp **`Chay-Mac.command`**. Trình duyệt tự mở <http://localhost:3900>. Giữ cửa sổ Terminal mở trong lúc dùng.

MacBook chip M1–M4 dùng GPU qua **MPS**, không cần cài gì thêm.

---

## 🐧 Cài đặt trên Linux

```bash
sudo apt install -y git curl unzip ffmpeg      # Ubuntu/Debian; distro khác dùng trình quản lý gói tương ứng
git clone https://github.com/locphamnguyen/VoiceStudio-VN.git ~/VoiceStudio
cd ~/VoiceStudio
./cai-dat.sh        # cài đặt (chỉ 1 lần)
./chay.sh           # mở VoiceStudio → http://localhost:3900
```

Có card NVIDIA: cài driver NVIDIA (ví dụ `sudo ubuntu-drivers autoinstall`) **trước** khi chạy `./cai-dat.sh` để bộ cài chọn đúng bản GPU.

<details>
<summary><strong>Chạy bằng Docker (cho máy chủ)</strong></summary>

Docker vẫn dùng được như bản gốc — xem [docs/install/docker.md](docs/install/docker.md). Cổng đăng nhập bật sẵn; tài khoản lưu trong thư mục dữ liệu (`accounts.db`), nên nhớ gắn volume cho thư mục dữ liệu để không mất tài khoản khi tạo lại container.

</details>

---

## 🚀 Lần đầu sử dụng

1. Trình duyệt mở trang **Đăng nhập**. Bấm **Đăng ký**, điền họ tên, email, mật khẩu (ít nhất 10 ký tự).
   **Người đăng ký đầu tiên tự động là Quản trị viên** và dùng được ngay.
2. Vào màn hình chính, VoiceStudio sẽ hướng dẫn cài **FFmpeg** và **tải model giọng nói** (vài GB, chỉ tải một lần). Bấm đồng ý và chờ thanh tiến trình chạy hết.
3. Mở **Nhân bản giọng** → chọn giọng mẫu có sẵn hoặc tải lên một đoạn ghi âm sạch 5–15 giây → nhập văn bản → **Tạo**.

Mẹo: ghi âm mẫu ở nơi yên tĩnh, nói tự nhiên, không nhạc nền — giọng nhân bản sẽ giống hơn rất nhiều.

---

## 🔐 Đăng ký, đăng nhập và quản lý thành viên

Lớp tài khoản viết theo mô hình của [Vonia](https://github.com/locphamnguyen/vonia):

| Quy tắc | Chi tiết |
|---|---|
| Ai là Quản trị viên? | **Người đăng ký đầu tiên.** Có thể giới hạn bằng `VOICESTUDIO_ADMIN_EMAILS` (xem [cấu hình](#-cấu-hình-nâng-cao-tệp-env)). |
| Người đăng ký sau | Ở trạng thái **Chờ duyệt** cho tới khi Quản trị viên bấm **Duyệt**. |
| Đăng nhập bằng | Email + mật khẩu, hoặc **Google** (nếu đã cấu hình). |
| Sai mật khẩu | Sai 5 lần liên tiếp → tạm khoá đăng nhập email đó 15 phút. |
| Phiên đăng nhập | Giữ 30 ngày kể từ lần dùng cuối. Khoá tài khoản là người đó bị đăng xuất ngay. |
| Lưu ở đâu? | Tệp `accounts.db` (SQLite) trong thư mục dữ liệu — **không cần cài Redis hay Docker**. Mật khẩu chỉ lưu dạng băm PBKDF2. |

**Trong ứng dụng**, góc trên bên phải có tên bạn và các nút:

- 👤 **Tài khoản của tôi** — xem thông tin, **đổi mật khẩu**, đăng xuất.
- 👥 **Quản lý thành viên** (chỉ Quản trị viên) — các tab *Chờ duyệt / Đang hoạt động / Đã khoá / Tất cả*, với các nút **Duyệt · Khoá · Cấp quyền QTV · Gỡ quyền QTV · Xoá**. Hệ thống luôn giữ lại ít nhất một Quản trị viên và không cho tự khoá chính mình.
- ↪ **Đăng xuất**.

Thư mục dữ liệu (chứa `accounts.db`, giọng, dự án):

| Hệ điều hành | Đường dẫn |
|---|---|
| Windows | `%APPDATA%\OmniVoice` |
| macOS | `~/Library/Application Support/OmniVoice` |
| Linux | `~/.omnivoice` |

**Quên mật khẩu Quản trị viên?** Nhờ một Quản trị viên khác đặt lại bằng cách xoá rồi để bạn đăng ký lại; nếu chỉ có một mình, tắt VoiceStudio, xoá tệp `accounts.db` trong thư mục dữ liệu rồi mở lại — người đăng ký đầu tiên sau đó lại là Quản trị viên. (Giọng và dự án **không** bị mất.)

**Ứng dụng desktop (Electron)** của bản gốc chạy cho một người trên chính máy đó nên **tự tắt** đăng nhập; tài khoản áp dụng cho bản chạy qua trình duyệt (các tệp `Chay…` ở trên, `bun run dev:web`, Docker).

<details>
<summary><strong>Bật đăng nhập bằng Google</strong></summary>

1. Vào [Google Cloud Console](https://console.cloud.google.com/) → *APIs & Services → Credentials → Create credentials → OAuth client ID*, loại **Web application**.
2. Ở *Authorized redirect URIs* thêm: `<địa-chỉ-của-bạn>/account/google/callback`, ví dụ `https://voice.congty.example/account/google/callback`.
3. Thêm vào tệp `.env` (xem mục dưới):
   ```ini
   GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxxxxxx
   VOICESTUDIO_PUBLIC_URL=https://voice.congty.example
   ```
4. Khởi động lại VoiceStudio — nút **Tiếp tục với Google** sẽ hiện trên trang đăng nhập.

Google chỉ chấp nhận `http://localhost` hoặc địa chỉ **https** làm redirect URI.

</details>

---

## 📣 Thông báo cập nhật và gọi-về trang trung tâm

Khi có bản mới hoặc tin cần biết, một **dải thông báo mỏng** hiện ở **cạnh dưới vùng làm việc** (ngay trên chân trang), trên cả Windows, macOS, Linux và bản trình duyệt. Không có gì để báo thì dải ẩn hẳn.

Đặt ở cạnh dưới (không phải cạnh trên) vì cạnh trên của cửa sổ là thanh tiêu đề dùng để kéo cửa sổ và có nút hệ thống của macOS — một dải bấm được ở đó sẽ hoặc chặn thao tác kéo, hoặc không bấm được.

Để có thông báo, VoiceStudio định kỳ (30 giây sau khi mở, rồi mỗi 12 giờ) gọi về trang trung tâm của dự án và gửi **đúng hai thứ**:

| Trường | Là gì |
|---|---|
| `instanceId` | chuỗi ngẫu nhiên sinh lần đầu chạy, lưu ở tệp `instance_id` trong thư mục dữ liệu — để đếm "một máy = một bản cài" |
| `version` | số phiên bản VoiceStudio đang chạy |

**Không gửi** gì về người dùng, tài khoản, giọng nói, văn bản hay cấu hình. Phía nhận **không lưu địa chỉ IP**. Máy không có mạng thì bỏ qua êm, không ảnh hưởng gì đến việc dùng.

---

## 🌐 Cho nhiều người dùng chung trong mạng nội bộ

Muốn cả văn phòng dùng chung một máy có card mạnh:

- **Windows**: mở PowerShell trong thư mục VoiceStudio, gõ `.\ChayVoiceStudio-Windows.cmd --lan`
- **macOS / Linux**: `./chay.sh --lan`

Cửa sổ sẽ in ra địa chỉ dạng `http://192.168.1.20:3900`. Người khác mở địa chỉ đó trên trình duyệt, bấm **Đăng ký**, rồi Quản trị viên vào **Quản lý thành viên** để duyệt.

- Windows có thể hỏi cho phép qua **Tường lửa (Firewall)** — chọn *Private networks* rồi **Allow**.
- **Đừng mở thẳng cổng 3900 ra Internet.** Muốn dùng từ xa, đặt sau một reverse proxy có **HTTPS** (Caddy, nginx, Cloudflare Tunnel, Tailscale…). Khi truy cập bằng tên miền riêng, thêm tên miền đó vào `OMNIVOICE_ALLOWED_HOSTS` trong `.env`.

---

## ⚙️ Cấu hình nâng cao (tệp `.env`)

Tạo tệp tên `.env` ở thư mục gốc VoiceStudio (cùng chỗ với `ChayVoiceStudio-Windows.cmd`), mỗi dòng một cặp `TÊN=giá trị`. Tệp được đọc mỗi lần mở VoiceStudio. Tất cả đều **không bắt buộc**:

```ini
# Chỉ những email này mới có thể trở thành Quản trị viên đầu tiên
# (NÊN đặt nếu máy mở cho nhiều người — chặn người lạ đăng ký trước bạn).
VOICESTUDIO_ADMIN_EMAILS=ban@congty.example

# Chỉ cho email thuộc tên miền này đăng ký / đăng nhập.
VOICESTUDIO_ALLOWED_DOMAIN=congty.example

# Tắt hẳn đăng nhập (chỉ khi dùng một mình trên máy, KHÔNG mở ra mạng).
VOICESTUDIO_ACCOUNTS=off

# Đăng nhập Google (xem mục trên)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
VOICESTUDIO_PUBLIC_URL=

# Tên miền riêng khi đứng sau reverse proxy
OMNIVOICE_ALLOWED_HOSTS=voice.congty.example

# Bị chặn Hugging Face? Dùng mirror:
HF_ENDPOINT=https://hf-mirror.com

# API key cho phần mềm khác (n8n, MCP, script) gọi API mà không cần đăng nhập
OMNIVOICE_API_KEY=mot-chuoi-bi-mat-dai
```

Phần mềm khác gọi API bằng header `Authorization: Bearer <OMNIVOICE_API_KEY>`. Danh sách API: [docs/speech-platform.md](docs/speech-platform.md), MCP: [docs/mcp.md](docs/mcp.md).

---

## 🔄 Cập nhật lên bản mới

- Tải bằng ZIP: tải ZIP mới, giải nén **đè** lên thư mục cũ (giữ nguyên thư mục `.venv` và tệp `.env`), rồi bấm đúp lại `CaiDat-…`.
- Tải bằng Git: `git pull` rồi chạy lại `CaiDat-…` / `./cai-dat.sh`.

Giọng, dự án, tài khoản nằm trong thư mục dữ liệu (xem bảng ở trên) nên **không bị ảnh hưởng** khi cập nhật.

---

## 🗑️ Gỡ cài đặt

1. Xoá thư mục VoiceStudio (ví dụ `C:\VoiceStudio`) và lối tắt ngoài Desktop.
2. (Tuỳ chọn) Xoá thư mục dữ liệu nếu muốn xoá cả giọng, dự án, tài khoản.
3. (Tuỳ chọn) Model tải về nằm trong bộ nhớ đệm Hugging Face (`%USERPROFILE%\.cache\huggingface` hoặc `~/.cache/huggingface`), có thể xoá để lấy lại dung lượng.

---

## 🛠️ Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Bấm đúp `.cmd` thì cửa sổ chớp rồi tắt | Mở PowerShell trong thư mục, gõ `.\CaiDat-Windows.cmd` để xem lỗi. |
| `uv` / `bun` "không được nhận dạng" | Đóng cửa sổ, mở lại và chạy lại tệp cài đặt (PATH mới chỉ có hiệu lực ở cửa sổ mới). |
| Lỗi tải thư viện / `tunnel error` / timeout | Mạng chặn hoặc chập chờn — thử mạng khác hoặc chạy lại; bước đã xong sẽ được bỏ qua. |
| Tải model chậm / không tải được | Thêm `HF_ENDPOINT=https://hf-mirror.com` vào `.env`, mở lại. |
| Có card NVIDIA nhưng vẫn chạy CPU | Cập nhật driver NVIDIA, chạy lại tệp cài đặt. |
| Trình duyệt báo *không kết nối được* | Chờ thêm 30–60 giây (lần đầu khởi động lâu), rồi tải lại trang. Kiểm tra cửa sổ đen còn mở. |
| *Port 3900 đang bị dùng* | Đã có một VoiceStudio đang chạy — dùng cửa sổ đó, hoặc đổi cổng: `PORT=4000 ./chay.sh` (macOS/Linux) hoặc `powershell -ExecutionPolicy Bypass -File scripts\vn\chay.ps1 -Port 4000` (Windows). |
| Máy khác trong mạng không vào được | Chạy với `--lan`, cho phép qua Firewall, dùng đúng địa chỉ IP cửa sổ in ra. |
| *Request refused: … unrecognized host name* | Truy cập bằng tên miền riêng → thêm tên miền vào `OMNIVOICE_ALLOWED_HOSTS`. |
| Quên mật khẩu | Xem mục [Đăng nhập & thành viên](#-đăng-ký-đăng-nhập-và-quản-lý-thành-viên). |
| Bị khoá đăng nhập | Sai mật khẩu 5 lần → chờ 15 phút. |

Một số thông báo lỗi kỹ thuật sâu bên trong (từ máy chủ Python hoặc từ model) vẫn bằng tiếng Anh như bản gốc — khi gặp, hãy chụp màn hình cửa sổ đen và trang lỗi để được hỗ trợ. Hướng dẫn chi tiết hơn (tiếng Anh): [docs/install/troubleshooting.md](docs/install/troubleshooting.md).

---

## 🔁 Khác gì so với bản gốc

Bản gốc [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) là ứng dụng rất mạnh nhưng hướng tới người dùng kỹ thuật: hướng dẫn tiếng Anh, chạy từ mã nguồn phải tự gõ `bun install`, `bun run setup:api`, `bun run dev:web`… và chạy hai máy chủ phát triển cùng lúc. Bản này viết lại phần "bao quanh" để người không rành kỹ thuật dùng được:

| | Bản gốc | Bản tiếng Việt này |
|---|---|---|
| Ngôn ngữ giao diện | Đoán theo trình duyệt, mặc định tiếng Anh | **Luôn mở bằng tiếng Việt** (vẫn đổi được), dịch nốt các chuỗi còn sót |
| Cài từ mã nguồn | 4–5 lệnh, tự cài bun/uv/Python | **Bấm đúp 1 tệp** (`CaiDat-Windows.cmd` / `CaiDat-Mac.command` / `./cai-dat.sh`) |
| Chạy | `bun run dev:web` (2 tiến trình, cổng 3900 + 3901) | **Bấm đúp 1 tệp**, 1 máy chủ duy nhất ở cổng 3900, tự mở trình duyệt, có lối tắt Desktop |
| Thông báo cập nhật | Kiểm tra bản mới của ứng dụng desktop qua GitHub Releases | Dải thông báo từ trang trung tâm cho mọi bản cài (gửi mã bản cài + số phiên bản) |
| Nhiều người dùng chung | PIN chia sẻ hoặc API key, không có tài khoản | **Đăng ký / đăng nhập** (email + Google), Quản trị viên duyệt thành viên |
| Cấu hình | Biến môi trường hệ thống | Tệp `.env` cạnh tệp chạy, có ví dụ sẵn |
| Hướng dẫn | Tiếng Anh, chia nhiều trang | README tiếng Việt từng bước, bảng xử lý sự cố |

Phần lõi (model, lồng tiếng, API, MCP…) **giữ nguyên** để dễ đồng bộ các bản cập nhật từ bản gốc. Các thay đổi chính nằm ở:

- `backend/core/accounts.py`, `account_gate.py`, `account_pages.py`, `backend/api/routers/accounts.py` — tài khoản (có test `tests/test_accounts.py`).
- `backend/services/phone_home.py`, `backend/core/announcement.py`, `components/app-shell/server-announcement-banner.tsx`, `deploy/phone-home-worker/` — gọi-về + dải thông báo, port từ ZaloCRM (có test `tests/test_phone_home.py`).
- `electron/src/renderer/src/i18n/` — tiếng Việt mặc định; `components/app-shell/account-menu.tsx` — nút tài khoản.
- `CaiDat-*.cmd|command`, `Chay*.cmd|command`, `cai-dat.sh`, `chay.sh`, `scripts/vn/` — bộ cài / chạy.

<details>
<summary><strong>Dành cho lập trình viên</strong></summary>

```bash
bun install
bun run setup:api        # cài Python + PyTorch đúng loại máy
bun run dev:web          # backend :3900 + giao diện Vite :3901 (có đăng nhập)
bun run dev              # ứng dụng desktop Electron (không có đăng nhập)
uv run pytest tests/test_accounts.py
bun run --cwd electron test
```

Đồng bộ từ bản gốc: `git remote add upstream https://github.com/debpalash/VoiceStudio.git && git fetch upstream && git merge upstream/main`. Tài liệu kỹ thuật bản gốc: [README_EN.md](README_EN.md), [electron/README.md](electron/README.md). Agent skills của bản gốc: `npx skills add debpalash/VoiceStudio`. Cộng đồng bản gốc: [Discord](https://discord.gg/bzQavDfVV9).

</details>

---

## 📜 Bản quyền và sử dụng có trách nhiệm

- Mã nguồn theo giấy phép **[AGPL-3.0](LICENSE)** như bản gốc — bản sửa đổi này cũng phải công khai mã nguồn khi cung cấp cho người khác dùng qua mạng. Chi tiết: [LICENSE-NOTICE.md](LICENSE-NOTICE.md).
- Bản quyền phần gốc thuộc tác giả [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) và [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice). Mỗi model có giấy phép riêng — kiểm tra trước khi dùng cho mục đích thương mại.
- **Chỉ nhân bản giọng của người đã đồng ý.** Không dùng để giả mạo, lừa đảo hay vi phạm pháp luật.
