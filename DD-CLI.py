#!/usr/bin/env python3
import subprocess
import re
import os
import argparse
import sys
from datetime import datetime

class DDUtilityCLI:
    def __init__(self):
        self.disk_info = {}
        self.selected_source_disk = None
        self.selected_destination_disk = None
        self.selected_file = None
        self.image_path = None
        self.total_size = 0
        self.cancelled = False
        self.process = None

    def get_disk_info(self):
        try:
            disk_details = subprocess.check_output(
                ["lsblk", "-dpno", "NAME,SIZE,TYPE,MODEL"]
            ).decode().strip().split("\n")
            
            disk_info = {}
            disk_choices = []
            
            for i, line in enumerate(disk_details):
                if line.startswith('/dev/sd') or line.startswith('/dev/mmcblk') or line.startswith('/dev/loop'):
                    parts = line.split()
                    disk_path = parts[0]
                    disk_size = parts[1]
                    disk_type = parts[2]
                    disk_model = ' '.join(parts[3:]) if len(parts) > 3 else 'Unknown'
                    
                    disk_info[disk_path] = {
                        'size': disk_size,
                        'model': disk_model,
                        'type': disk_type
                    }
                    disk_choices.append((i, disk_path, disk_size, disk_model))
            
            self.disk_info = disk_info
            return disk_choices
            
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to list disks: {e}")
            return []

    def list_disks(self):
        disks = self.get_disk_info()
        if not disks:
            print("No disks found!")
            return
        
        print("\nAvailable disks:")
        print(f"{'#':<3} {'Device':<15} {'Size':<10} {'Model'}")
        print("-" * 50)
        for i, path, size, model in disks:
            print(f"{i:<3} {path:<15} {size:<10} {model}")

    def select_disk(self, prompt):
        disks = self.get_disk_info()
        if not disks:
            return None
            
        while True:
            self.list_disks()
            try:
                choice = input(f"\n{prompt} (enter number or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    return None
                
                choice = int(choice)
                if 0 <= choice < len(disks):
                    return disks[choice][1]
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def confirm_operation(self, message):
        parts = message.split('\n')
        formatted_message = []
        for part in parts:
            if "WARNING:" in part:
                formatted_message.append(f"\033[38;5;201m{part}\033[0m")
            else:
                formatted_message.append(part)
        
        print("\n" + "\n".join(formatted_message) + "\n")
        response = input("Are you sure you want to continue? (y/N): ").strip().lower()
        return response == 'y'

    def update_progress(self, line):
        match = re.search(r'(\d+) bytes', line)
        if match:
            copied_bytes = int(match.group(1))
            copied_mb = copied_bytes / (1024 * 1024)
            if self.total_size > 0:
                progress_percentage = min((copied_bytes / self.total_size) * 100, 100)
                print(f"\r\033[38;5;82mCopied: {int(copied_mb):04d} MB, {progress_percentage:.0f}% Completed\033[0m", end='')

    def execute_dd(self, src, dest):
        try:
            self.process = subprocess.Popen(
                ["sudo", "dd", f"if={src}", f"of={dest}", "bs=4M", "conv=fdatasync", "status=progress"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            while True:
                if self.cancelled:
                    break
                    
                line = self.process.stderr.readline()
                if not line:
                    break
                self.update_progress(line.strip())
            
            self.process.wait()
            if self.cancelled:
                print("\nOperation cancelled")
                return False
            elif self.process.returncode == 0:
                print("\nOperation completed successfully")
                return True
            else:
                raise subprocess.CalledProcessError(self.process.returncode, self.process.args)
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\nOperation failed: {error_msg}")
            return False
        finally:
            self.process = None

    def file_to_disk(self):
        print("\nFile to Disk Operation")
        print("----------------------")
        
        file_path = input("Enter path to the file to flash: ").strip()
        if not os.path.exists(file_path):
            print("Error: File does not exist!")
            return
            
        self.selected_file = file_path
        self.total_size = os.path.getsize(file_path)
        
        dest_disk = self.select_disk("Select destination disk")
        if not dest_disk:
            return
            
        if not self.confirm_operation(
            f"You are about to flash:\n{os.path.basename(file_path)}\n"
            f"to:\n{dest_disk}\n"
            f"WARNING: This will destroy all data on the destination disk!"
        ):
            return
            
        print("\nStarting file to disk operation...\n")
        self.execute_dd(file_path, dest_disk)

    def disk_to_disk(self):
        print("\nDisk to Disk Operation")
        print("---------------------")
        
        src_disk = self.select_disk("Select source disk")
        if not src_disk:
            return
            
        try:
            self.total_size = int(subprocess.check_output(
                ["sudo", "blockdev", "--getsize64", src_disk]
            ).strip())
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to get size of source disk: {e}")
            return
            
        dest_disk = self.select_disk("Select destination disk")
        if not dest_disk:
            return
            
        if not self.confirm_operation(
            f"You are about to clone:\n{src_disk}\n"
            f"to:\n{dest_disk}\n"
            f"WARNING: This will destroy all data on the destination disk!"
        ):
            return
            
        print("\nStarting disk to disk operation...\n")
        self.execute_dd(src_disk, dest_disk)

    def create_partition_table(self):
        print("\nCreate Partition Table")
        print("----------------------")
        
        disk = self.select_disk("Select disk to create partition table on")
        if not disk:
            return
            
        print("\nPartition table types:")
        print("\033[38;5;201m1.\033[0m \033[38;5;82mMBR (msdos)\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82mGPT\033[0m")
        choice = input("\033[38;5;82mSelect partition table type \033[0m\033[38;5;201m(1-2)\033[0m\033[38;5;82m: \033[0m").strip()
        
        if choice == '1':
            table_type = "msdos"
        elif choice == '2':
            table_type = "gpt"
        else:
            print("Invalid selection")
            return
            
        if not self.confirm_operation(
            f"You are about to create a {table_type} partition table on:\n{disk}\n"
            f"WARNING: This will destroy all data on this disk!"
        ):
            return
            
        print(f"\nCreating {table_type} partition table on {disk}...\n")
        try:
            result = subprocess.run(
                ["sudo", "parted", "-s", disk, "mklabel", table_type],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"Successfully created {table_type} partition table on {disk}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"Failed to create partition table: {error_msg}")

    def format_disk(self):
        print("\nFormat Disk/Partition")
        print("---------------------")
        
        disk = self.select_disk("Select disk/partition to format")
        if not disk:
            return
            
        print("\nAvailable filesystems:")
        filesystems = [
            ("1", "FAT16", "fat16"), ("2", "FAT32", "fat32"), ("3", "exFAT", "exfat"),
            ("4", "NTFS", "ntfs"), ("5", "BTRFS", "btrfs"), ("6", "EXT2", "ext2"),
            ("7", "EXT3", "ext3"), ("8", "EXT4", "ext4"), ("9", "LUKS", "luks")
        ]
        
        for num, name, _ in filesystems:
            print(f"\033[38;5;201m{num}.\033[0m \033[38;5;82m{name}\033[0m")
            
        choice = input("\033[38;5;82mSelect filesystem \033[0m\033[38;5;201m(1-9)\033[0m\033[38;5;82m: \033[0m").strip()
        selected = None
        
        for num, name, fs_type in filesystems:
            if choice == num:
                selected = fs_type
                break
                
        if not selected:
            print("Invalid selection")
            return
            
        if not self.confirm_operation(
            f"You are about to format:\n{disk}\n"
            f"as {selected.upper()}\n"
            f"WARNING: This will destroy all data on this disk/partition!"
        ):
            return
            
        print(f"\nFormatting {disk} as {selected}...\n")
        try:
            if selected == "luks":
                process = subprocess.Popen(
                    ["sudo", "cryptsetup", "luksFormat", disk],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input="YES\n")
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args)
            else:
                if selected.startswith("fat"):
                    cmd = ["sudo", "mkfs.vfat", "-F", selected[3:], disk]
                elif selected == "exfat":
                    cmd = ["sudo", "mkfs.exfat", disk]
                elif selected == "ntfs":
                    cmd = ["sudo", "mkfs.ntfs", "-Q", disk]
                elif selected.startswith("ext"):
                    cmd = ["sudo", f"mkfs.{selected}", disk]
                elif selected == "btrfs":
                    cmd = ["sudo", "mkfs.btrfs", "-f", disk]
                
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            print(f"Successfully formatted {disk} as {selected}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"Failed to format disk: {error_msg}")

    def secure_erase(self):
        print("\nSecure Erase Disk")
        print("----------------")
        
        disk = self.select_disk("Select disk to securely erase")
        if not disk:
            return
            
        print("\nErase methods:")
        print("\033[38;5;201m1.\033[0m \033[38;5;82m/dev/zero (1 pass)\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82m/dev/random (3 passes)\033[0m")
        print("\033[38;5;201m3.\033[0m \033[38;5;82m/dev/urandom (7 passes)\033[0m")
        choice = input("\033[38;5;82mSelect erase method \033[0m\033[38;5;201m(1-3)\033[0m\033[38;5;82m: \033[0m").strip()
        
        if choice == '1':
            source = "/dev/zero"
            passes = 1
        elif choice == '2':
            source = "/dev/random"
            passes = 3
        elif choice == '3':
            source = "/dev/urandom"
            passes = 7
        else:
            print("Invalid selection")
            return
            
        if not self.confirm_operation(
            f"You are about to securely erase:\n{disk}\n"
            f"with {passes} passes of {source}\n"
            f"WARNING: This will destroy all data on this disk!"
        ):
            return
            
        try:
            self.total_size = int(subprocess.check_output(
                ["sudo", "blockdev", "--getsize64", disk]
            ).strip())
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to get disk size: {e}")
            return
            
        print(f"\nErasing {disk} with {passes} passes of {source}...\n")
        try:
            for i in range(passes):
                if self.cancelled:
                    break
                    
                print(f"\nPass {i+1} of {passes} with {source}")
                
                process = subprocess.Popen(
                    ["sudo", "dd", f"if={source}", f"of={disk}", "bs=1M", "status=progress"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.process = process
                
                while True:
                    if self.cancelled:
                        process.terminate()
                        break
                        
                    line = process.stderr.readline()
                    if not line:
                        break
                    
                    # Update progress
                    match = re.search(r'(\d+) bytes', line)
                    if match:
                        copied_bytes = int(match.group(1))
                        progress = (i * 100 + (copied_bytes / self.total_size * 100)) / passes
                        print(f"\r\033[38;5;82mProgress: {progress:.1f}%\033[0m", end='')
                
                process.wait()
                if process.returncode != 0 and not self.cancelled:
                    raise subprocess.CalledProcessError(process.returncode, process.args)

            if self.cancelled:
                print("\nSecure erase cancelled")
            else:
                print(f"\nSecure erase completed successfully with {passes} passes")
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\nSecure erase failed: {error_msg}")

    def create_disk_image(self):
        print("\nCreate Disk Image")
        print("----------------")
        
        disk = self.select_disk("Select disk to create image from")
        if not disk:
            return
            
        disk_model = self.disk_info[disk]['model'].replace(" ", "_")
        disk_size = self.disk_info[disk]['size'].replace(" ", "")
        default_name = f"image-of-{disk_model}-{disk_size}.img"
        
        dest_dir = input(f"Enter directory to save image (default name: {default_name}): ").strip()
        if not dest_dir:
            print("No directory specified")
            return
            
        self.image_path = os.path.join(dest_dir, default_name)
        
        if not self.confirm_operation(
            f"You are about to create a disk image with these details:\n"
            f"Source Disk: {disk}\n"
            f"Destination: {self.image_path}\n"
            f"Disk Model: {self.disk_info[disk]['model']}\n"
            f"Disk Size: {self.disk_info[disk]['size']}"
        ):
            return
            
        try:
            self.total_size = int(subprocess.check_output(
                ["sudo", "blockdev", "--getsize64", disk]
            ).strip())
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to get disk size: {e}")
            return
            
        print(f"\nCreating disk image from {disk} to {self.image_path}...\n")
        try:
            process = subprocess.Popen(
                ["sudo", "dd", f"if={disk}", f"of={self.image_path}", "bs=4M", "status=progress"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.process = process
            
            while True:
                if self.cancelled:
                    process.terminate()
                    # Remove partially created image
                    if os.path.exists(self.image_path):
                        os.remove(self.image_path)
                    break
                    
                line = process.stderr.readline()
                if not line:
                    break
                
                # Update progress
                match = re.search(r'(\d+) bytes', line)
                if match:
                    copied_bytes = int(match.group(1))
                    progress_percentage = min((copied_bytes / self.total_size) * 100, 100)
                    print(f"\r\033[38;5;82mProgress: {progress_percentage:.1f}%\033[0m", end='')
            
            process.wait()
            if self.cancelled:
                print("\nDisk imaging cancelled")
            elif process.returncode == 0:
                print(f"\nDisk image created successfully at:\n{self.image_path}")
            else:
                raise subprocess.CalledProcessError(process.returncode, process.args)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            # Remove failed image file if it exists
            if os.path.exists(self.image_path):
                os.remove(self.image_path)
            print(f"\nDisk imaging failed: {error_msg}")

    def cancel_operation(self):
        if self.process:
            self.process.terminate()
        self.cancelled = True

def main():
    parser = argparse.ArgumentParser(description="DD Utility CLI Tool")
    parser.add_argument(
        '-l', '--list-disks',
        action='store_true',
        help="List available disks and exit"
    )
    args = parser.parse_args()
    
    utility = DDUtilityCLI()
    
    if args.list_disks:
        utility.list_disks()
        sys.exit(0)
    
    while True:
        print("\n\033[38;5;201mDD Utility - CLI\033[0m")
        print(" ")
        print("\033[38;5;201m1.\033[0m \033[38;5;82mFile to Disk\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82mDisk to Disk\033[0m")
        print("\033[38;5;201m3.\033[0m \033[38;5;82mCreate Partition Table\033[0m")
        print("\033[38;5;201m4.\033[0m \033[38;5;82mFormat Disk/Partition\033[0m")
        print("\033[38;5;201m5.\033[0m \033[38;5;82mSecure Erase Disk\033[0m")
        print("\033[38;5;201m6.\033[0m \033[38;5;82mCreate Disk Image\033[0m")
        print("\033[38;5;201m7.\033[0m \033[38;5;82mList Disks\033[0m")
        print("\033[38;5;201m8.\033[0m \033[38;5;82mExit\033[0m")
        
        choice = input("\n\033[38;5;82mSelect operation \033[0m\033[38;5;201m(1-8)\033[0m\033[38;5;82m: \033[0m").strip()
        
        try:
            if choice == '1':
                utility.file_to_disk()
            elif choice == '2':
                utility.disk_to_disk()
            elif choice == '3':
                utility.create_partition_table()
            elif choice == '4':
                utility.format_disk()
            elif choice == '5':
                utility.secure_erase()
            elif choice == '6':
                utility.create_disk_image()
            elif choice == '7':
                utility.list_disks()
            elif choice == '8':
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            utility.cancel_operation()
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
