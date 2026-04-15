fn main() {
    let mut res = winres::WindowsResource::new();
    res.set_icon("icon.ico"); //https://icon-icons.com/icon/email-at/57328
    res.compile().unwrap();
}