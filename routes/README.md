Test trước trong folder Original.
Trước khi test cần:
B1. Chạy server db firebase local
B2. Cho một số file vào folder Original.
B3. Chạy trước file APIcalling trong routes.
B4. Vào postman để test API bằng link: ```ws://localhost:8000/ws/Original``
B5. Chạy file TrackingFolder.py.
B6. Vào trong postman để xem kết quả được trả về
Nhận xét về kết quả cho ra: 
- Thỏa mãn về điều kiện thời gian thời gian từ mới nhất đến những cái cũ được đưa vào.
- Thỏa mãn về đường link được đưa ra để sử dụng. 
Yếu điểm:
- Chưa đưa ra được chỉ mỗi url.
- Chưa phản ứng đến trường hợp bị crash.
Hình ảnh khi test được:
![alt text](image.png)
Sau khi áp dụng dùng dưới websocket thì hình ảnh khi ra ở đây:
![alt text](image-1.png)
Cho thấy code hoạt động rất ổn trong việc đây dữ liệu vào và khá là mượt mà mặt dù có một chút giật giật khi đẩy ảnh vào nhưng xem như không đáng kể.

Hiện tại thì cần phải testing cho AIService. Thêm folder photobooth và đẩy lại những khám phá cho bên FE để thêm vào cho kịp tiến độ (1/9/2025)
