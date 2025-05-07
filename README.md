# DD-CLI - Disk Operations Tool  

**A powerful Python-based command-line tool for disk operations, providing a user-friendly interface for common `dd` tasks.**  

---

## 📥 Installation  

Run the following commands to quickly set up and launch DD-CLI:  

```bash
git clone https://github.com/GlitchLinux/dd_py_CLI.git
cd dd_py_CLI
python3 DD-CLI.py
```

## Dependecies 

## Debian & Ubuntu

```bash
sudo apt install -y python3 python3-pip git pv dosfstools parted cryptsetup lsblk
```
## Arch 

```bash
sudo pacman -S python python-pip git pv dosfstools parted cryptsetup lsblk
```
## Fedora

```bash
sudo dnf install -y python3 python3-pip git pv dosfstools parted cryptsetup lsblk
```
## openSUSE

```bash
sudo zypper install -y python3 python3-pip git pv dosfstools parted cryptsetup lsblk
```
## Alpine

```bash
sudo apk add python3 py3-pip git pv dosfstools parted cryptsetup lsblk
```
---

## 🚀 Features  

### 🔹 **Disk Operations**  
- **Read/Write Disk Images** – Create backups or restore disk images with ease.  
- **Disk Cloning** – Clone entire disks or partitions securely.  
- **Data Wiping** – Securely erase disks or partitions.  

### 🔹 **User-Friendly Interface**  
- **Interactive CLI** – No need to memorize `dd` commands; guided prompts simplify operations.  
- **Progress Tracking** – Real-time progress display for long-running operations.  
- **Error Handling** – Prevents accidental data loss with confirmation prompts.  

### 🔹 **Advanced Options**  
- **Block Size Control** – Optimize read/write speeds by adjusting block sizes.  
- **Checksum Verification** – Ensure data integrity with hash checks (MD5, SHA-256).  
- **Logging Support** – Keep records of operations for debugging and auditing.  

### 🔹 **Cross-Platform**  
- Works on **Linux, macOS, and Windows** (with Python 3 support).  
- Lightweight, no heavy dependencies.  

---

## 🛠️ Usage  

After launching `DD-CLI.py`, follow the interactive prompts to:  
1. **Select source & destination disks/partitions.**  
2. **Choose operation type (clone, backup, restore, wipe).**  
3. **Configure advanced settings (block size, checksum, etc.).**  
4. **Confirm and execute.**  

*(Example: Clone `/dev/sda` to `/dev/sdb` with SHA-256 verification.)*  

---

## 📜 License  
Open-source (MIT).  

---

## 👤 Creator  
**gLiTcH Linux** © 2025  
🔗 **Repository:** [https://github.com/GlitchLinux/dd_py_CLI.git](https://github.com/GlitchLinux/dd_py_CLI.git)  

---

### ⚠️ Warning  
- **Use with caution!** Improper disk operations can lead to **data loss**.  
- Always double-check source/destination selections before confirming.  

--- 

🛡️ **A safer, smarter way to handle disk operations.** 🛡️
