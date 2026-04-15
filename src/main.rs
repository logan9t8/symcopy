use std::{
    collections::HashMap,
    env,
    fs,
    io::Write,
    process::{Command, Stdio},
};

use arboard::Clipboard;

fn main() -> Result<(), Box<dyn std::error::Error>> {

    // Check if fzf is available
    if Command::new("fzf").arg("--version").output().is_err() {
        eprintln!("Error: fzf is not installed or not in PATH.");
        std::process::exit(1);
    }

    // JSON
    let exe_path = std::env::current_exe()?;
    let exe_dir = exe_path.parent().ok_or("Failed to get exe directory")?;
    let json_path = exe_dir.join("unicode_ds.json");
    let json_str = fs::read_to_string(json_path)?;
    let map: HashMap<String, String> = serde_json::from_str(&json_str)?;

    // Fzf
    let query = env::args().nth(1);
    let mut cmd = Command::new("fzf");
    cmd.stdin(Stdio::piped())
        .stdout(Stdio::piped());
    if let Some(q) = query {
        cmd.arg("--query").arg(q);
    }
    let mut child = cmd.spawn()?;

    // Send "value    key" (nice aligned format)
    if let Some(stdin) = child.stdin.as_mut() {
        for (key, value) in &map {
            writeln!(stdin, "{:<3} {}", value, key)?;
        }
    }

    let output = child.wait_with_output()?;
    if !output.status.success() {
        return Ok(());
    }
    
    let selected = String::from_utf8(output.stdout)?
        .trim()
        .to_string();

    // Extract value (first column)
    let value = selected.split_whitespace().next().unwrap();
    let mut clipboard = Clipboard::new()?;
    clipboard.set_text(value.to_string())?;
    println!("Copied {}", value);

    Ok(())
}