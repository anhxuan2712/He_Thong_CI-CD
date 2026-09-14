# MÔ HÌNH HỆ THỐNG CI/CD CỦA CÔNG TY FTECH

![Mô hình hệ thống CI/CD FTECH](./images/mo_hinh_ci_cd_ftech.png)

## Continuous Integration (CI)

### Developer

Developer commit và push code lên nhánh (branch) của mình. Đây chính là sự kiện khiến GitLab tự động trigger pipeline ngay lập tức, dựa trên hành động push chứ không cần bấm nút "Run pipeline" thủ công. Sau khi pipeline chạy, developer theo dõi kết quả từng stage — pass hay fail. Nếu có stage fail, developer đọc log để xác định nguyên nhân, sửa code, rồi push lại; mỗi commit mới sẽ tự động kích hoạt một pipeline mới chạy lại từ đầu.

---

### GitLab CI

Sau khi GitLab nhận được sự kiện (push code hoặc tạo Merge Request), hệ thống sẽ trigger một pipeline mới. GitLab bắt đầu đọc file cấu hình `.gitlab-ci.yml` của dự án; khi gặp chỉ thị `include`, `GitLab` sẽ lấy các file template tương ứng từ repository trung tâm `gitlab-ci/ci-pipeline`, cụ thể là hai file `build-template.yml` và `devsecops-template.yml`, rồi merge (gộp) nội dung của chúng vào cấu hình pipeline của dự án.

Trong `build-template.yml` có ba job thực thi thực sự là `build-dev`, `build-staging`, `build-prod`, cùng với một job ẩn `.build_template` — tên job bắt đầu bằng dấu `.` nên GitLab **không** tạo job thật nào để chạy nó, mà chỉ dùng làm khuôn mẫu cấu hình. Khối nội dung của job ẩn này (`image`, `before_script`, `script`, `services`...) được đánh dấu bằng YAML anchor `&build`, và ba job thực thi ở trên tái sử dụng lại toàn bộ khối đó thông qua cú pháp merge key `<<: *build` — nhờ vậy logic build chỉ cần viết một lần duy nhất thay vì lặp lại ba lần. Mỗi job trong ba job này chỉ được kích hoạt khi nhánh Git khớp điều kiện `only` tương ứng (`dev`/`develop`, `staging`, hoặc `main`/`master`/`prod`/`tag`) — tại một thời điểm push, **chỉ đúng một trong ba job chạy**, không phải cả ba chạy song song.

Về mặt thực thi, job build sử dụng cơ chế Docker-in-Docker (DinD): container chính (image `docker:$DOCKER_VERSION`) chỉ chứa Docker CLI, dùng để chạy các lệnh trong `before_script`/`script`; các lệnh này được gửi qua mạng nội bộ của job đến một container service riêng (image `docker:$DOCKER_DIND_VERSION`, được đặt `alias: docker`) — container service này mới thực sự chứa Docker daemon và chịu trách nhiệm thực thi các thao tác build/push image.

Trong `devsecops-template.yml` khai báo biến toàn cục `RESULT` (`./result1.json`) làm cầu nối dữ liệu giữa hai job `dependency-check` và `upload-bom`, gồm 5 job chạy tuần tự theo đúng thứ tự khai báo trong `stages:` của project:

- **Job `detect-secrets`**: Dùng image nội bộ để quét mã nguồn tìm token, password hard-code; trước đó xoá `.git/` để chỉ quét code hiện tại, không quét lịch sử commit. Đây là job duy nhất (cùng `build`) có `allow_failure: false` — phát hiện secret là pipeline dừng ngay.
- **Job `dependency-check`**: Dùng Trivy quét lỗ hổng thư viện phụ thuộc mức HIGH/CRITICAL, bỏ qua lỗ hổng chưa có bản vá, xuất kết quả vào file `$RESULT` để job sau dùng.
- **Job `upload-bom`**: Lấy file này, gửi lên Dependency-Track qua HTTP POST để theo dõi lỗ hổng liên tục theo thời gian.
- **Job `sonarqube-check`**: Chạy Sonar Scanner phân tích chất lượng code (bug, code smell), gửi kết quả về SonarQube Server, có cache riêng để tăng tốc lần chạy sau.
- **Cuối cùng, `gitlabci-analyser`**: Chạy script nội bộ đo thời gian chờ hàng đợi và thời lượng job, phục vụ giám sát hạ tầng CI, cũng `allow_failure: true`.

> **Đáng lưu ý:** Cả 5 job đều có `only:` bị comment — hiện chạy trên **mọi nhánh**, khác với `build` vốn giới hạn theo nhánh cụ thể.
