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

    def list_disks(self, include_partitions=False):
        disks = self.get_disk_info()
        if not disks:
            print("\033[38;5;201mNo disks found!\033[0m")
            return
        
        print("\n\033[38;5;201mAvailable disks:\033[0m")
        print(" ")
        for i, path, size, model in disks:
            print("\033[38;5;201m{:<3}\033[0m \033[38;5;82m{:<15} {:<10} {}\033[0m".format(i, path, size, model))
            
            if include_partitions:
                try:
                    partitions = subprocess.check_output(
                        ["lsblk", "-pno", "NAME", path]
                    ).decode().strip().split("\n")
                    
                    if len(partitions) > 1:  # If there are partitions
                        for part in partitions[1:]:  # Skip the first line (disk itself)
                            part_info = subprocess.check_output(
                                ["lsblk", "-dpno", "NAME,SIZE,FSTYPE", part.strip()]
                            ).decode().strip()
                            part_parts = part_info.split()
                            print("   \033[38;5;201m->\033[0m \033[38;5;82m{:<15} {:<10} {}\033[0m".format(
                                part_parts[0], part_parts[1], part_parts[2] if len(part_parts) > 2 else "Unknown"
                            ))
                except subprocess.CalledProcessError:
                    pass

    def select_disk(self, prompt, include_partitions=False):
        disks = self.get_disk_info()
        if not disks:
            return None
            
        while True:
            self.list_disks(include_partitions)
            try:
                choice = input(f"\n\033[38;5;201m{prompt} (enter number or 'q' to quit): \033[0m").strip()
                if choice.lower() == 'q':
                    return None
                
                choice = int(choice)
                if 0 <= choice < len(disks):
                    return disks[choice][1]
                else:
                    print("\033[38;5;201mInvalid selection. Please try again.\033[0m")
            except ValueError:
                print("\033[38;5;201mPlease enter a valid number.\033[0m")

    def confirm_operation(self, message):
        parts = message.split('\n')
        formatted_message = []
        for part in parts:
            if part.startswith("You are about to") or part.startswith("to:"):
                formatted_message.append(f"\033[38;5;201m{part}\033[0m")
            elif "WARNING:" in part:
                formatted_message.append(f"\033[38;5;201m{part}\033[0m")
            else:
                formatted_message.append(f"\033[38;5;82m{part}\033[0m")
        
        print("\n" + "\n".join(formatted_message) + "\n")
        response = input("\033[38;5;82mAre you sure you want to continue? (y/N): \033[0m").strip().lower()
        print()
        return response == 'y'

    def update_progress(self, line):
        match = re.search(r'(\d+) bytes', line)
        if match:
            copied_bytes = int(match.group(1))
            copied_mb = copied_bytes / (1024 * 1024)
            if self.total_size > 0:
                progress_percentage = min((copied_bytes / self.total_size) * 100, 100)
                print(f"\r\033[38;5;201mCopied: \033[38;5;82m{int(copied_mb):04d} MB \033[38;5;201m{progress_percentage:.0f}% \033[38;5;82mCompleted\033[0m", end='')

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
                print("\n\033[38;5;201mOperation cancelled\033[0m")
                return False
            elif self.process.returncode == 0:
                print("\n\033[38;5;82mOperation completed successfully\033[0m")
                return True
            else:
                raise subprocess.CalledProcessError(self.process.returncode, self.process.args)
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\n\033[38;5;201mOperation failed: {error_msg}\033[0m")
            return False
        finally:
            self.process = None

    def file_to_disk(self):
        print("\n\033[38;5;201mFile to Disk Operation\033[0m")
        print(" ")
        
        file_path = input("\033[38;5;82mEnter path to the file to flash: \033[0m").strip()
        if not os.path.exists(file_path):
            print("\033[38;5;201mError: File does not exist!\033[0m")
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
            
        print("\n\033[38;5;201mStarting file to disk operation...\033[0m\n")
        self.execute_dd(file_path, dest_disk)

    def disk_to_disk(self):
        print("\n\033[38;5;201mDisk to Disk Operation\033[0m")
        print(" ")
        
        src_disk = self.select_disk("Select source disk")
        if not src_disk:
            return
            
        try:
            self.total_size = int(subprocess.check_output(
                ["sudo", "blockdev", "--getsize64", src_disk]
            ).strip())
        except subprocess.CalledProcessError as e:
            print(f"\033[38;5;201mError: Failed to get size of source disk: {e}\033[0m")
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
            
        print("\n\033[38;5;201mStarting disk to disk operation...\033[0m\n")
        self.execute_dd(src_disk, dest_disk)

    def create_partition_table(self):
        print("\n\033[38;5;201mCreate Partition Table\033[0m")
        print(" ")
        
        disk = self.select_disk("Select disk to create partition table on")
        if not disk:
            return
            
        print("\n\033[38;5;201mPartition table types:\033[0m")
        print("\033[38;5;201m1.\033[0m \033[38;5;82mMBR (msdos)\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82mGPT\033[0m")
        choice = input("\n\033[38;5;82mSelect partition table type \033[0m\033[38;5;201m(1-2)\033[0m\033[38;5;82m: \033[0m").strip()
        
        if choice == '1':
            table_type = "msdos"
        elif choice == '2':
            table_type = "gpt"
        else:
            print("\033[38;5;201mInvalid selection\033[0m")
            return
            
        if not self.confirm_operation(
            f"You are about to create a {table_type} partition table on:\n{disk}\n"
            f"WARNING: This will destroy all data on this disk!"
        ):
            return
            
        print(f"\n\033[38;5;201mCreating {table_type} partition table on {disk}...\033[0m\n")
        try:
            result = subprocess.run(
                ["sudo", "parted", "-s", disk, "mklabel", table_type],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"\033[38;5;82mSuccessfully created {table_type} partition table on {disk}\033[0m")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\033[38;5;201mFailed to create partition table: {error_msg}\033[0m")

    def format_disk(self):
        print("\n\033[38;5;201mFormat Disk/Partition\033[0m")
        print(" ")
        
        disk = self.select_disk("Select disk/partition to format", include_partitions=True)
        if not disk:
            return
            
        print("\n\033[38;5;201mAvailable filesystems:\033[0m")
        filesystems = [
            ("1", "FAT16", "fat16"), ("2", "FAT32", "fat32"), ("3", "exFAT", "exfat"),
            ("4", "NTFS", "ntfs"), ("5", "BTRFS", "btrfs"), ("6", "EXT2", "ext2"),
            ("7", "EXT3", "ext3"), ("8", "EXT4", "ext4"), ("9", "LUKS", "luks")
        ]
        
        for num, name, _ in filesystems:
            print(f"\033[38;5;201m{num}.\033[0m \033[38;5;82m{name}\033[0m")
            
        choice = input("\n\033[38;5;82mSelect filesystem \033[0m\033[38;5;201m(1-9)\033[0m\033[38;5;82m: \033[0m").strip()
        selected = None
        
        for num, name, fs_type in filesystems:
            if choice == num:
                selected = fs_type
                break
                
        if not selected:
            print("\033[38;5;201mInvalid selection\033[0m")
            return
            
        if not self.confirm_operation(
            f"You are about to format:\n{disk}\n"
            f"as {selected.upper()}\n"
            f"WARNING: This will destroy all data on this disk/partition!"
        ):
            return
            
        print(f"\n\033[38;5;201mFormatting {disk} as {selected}...\033[0m\n")
        try:
            if selected == "luks":
                # Prompt for passphrase
                passphrase = input("\033[38;5;82mEnter passphrase for LUKS encryption: \033[0m").strip()
                if not passphrase:
                    print("\033[38;5;201mPassphrase cannot be empty!\033[0m")
                    return
                
                # Create LUKS container
                process = subprocess.Popen(
                    ["sudo", "cryptsetup", "luksFormat", "--batch-mode", disk],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=passphrase + "\n" + passphrase + "\n")
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args)
                
                print("\033[38;5;82mLUKS container created successfully\033[0m")
                
                # Open the LUKS container
                mapper_name = os.path.basename(disk) + "_crypt"
                process = subprocess.Popen(
                    ["sudo", "cryptsetup", "open", disk, mapper_name],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=passphrase + "\n")
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args)
                
                print("\033[38;5;82mLUKS container opened at /dev/mapper/{}\033[0m".format(mapper_name))
                
                # Prompt for filesystem for the data partition
                print("\n\033[38;5;201mAvailable filesystems for the data partition:\033[0m")
                data_filesystems = [
                    ("1", "EXT4", "ext4"), ("2", "BTRFS", "btrfs"), ("3", "XFS", "xfs")
                ]
                
                for num, name, _ in data_filesystems:
                    print(f"\033[38;5;201m{num}.\033[0m \033[38;5;82m{name}\033[0m")
                    
                choice = input("\n\033[38;5;82mSelect filesystem for data partition \033[0m\033[38;5;201m(1-3)\033[0m\033[38;5;82m: \033[0m").strip()
                selected_fs = None
                
                for num, name, fs_type in data_filesystems:
                    if choice == num:
                        selected_fs = fs_type
                        break
                        
                if not selected_fs:
                    print("\033[38;5;201mInvalid selection\033[0m")
                    return
                
                # Format the data partition
                mapper_path = f"/dev/mapper/{mapper_name}"
                if selected_fs == "ext4":
                    cmd = ["sudo", "mkfs.ext4", mapper_path]
                elif selected_fs == "btrfs":
                    cmd = ["sudo", "mkfs.btrfs", "-f", mapper_path]
                elif selected_fs == "xfs":
                    cmd = ["sudo", "mkfs.xfs", "-f", mapper_path]
                
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                print(f"\033[38;5;82mSuccessfully formatted {mapper_path} as {selected_fs}\033[0m")
                
                # Close the LUKS container
                subprocess.run(["sudo", "cryptsetup", "close", mapper_name], check=True)
                print("\033[38;5;82mLUKS container closed\033[0m")
                
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

                print(f"\033[38;5;82mSuccessfully formatted {disk} as {selected}\033[0m")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\033[38;5;201mFailed to format disk: {error_msg}\033[0m")

    def secure_erase(self):
        print("\n\033[38;5;201mSecure Erase Disk\033[0m")
        print(" ")
        
        disk = self.select_disk("Select disk to securely erase")
        if not disk:
            return
            
        print("\n\033[38;5;201mErase methods:\033[0m")
        print("\033[38;5;201m1.\033[0m \033[38;5;82m/dev/zero (1 pass)\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82m/dev/random (3 passes)\033[0m")
        print("\033[38;5;201m3.\033[0m \033[38;5;82m/dev/urandom (7 passes)\033[0m")
        choice = input("\n\033[38;5;82mSelect erase method \033[0m\033[38;5;201m(1-3)\033[0m\033[38;5;82m: \033[0m").strip()
        
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
            print("\033[38;5;201mInvalid selection\033[0m")
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
            print(f"\033[38;5;201mError: Failed to get disk size: {e}\033[0m")
            return
            
        print(f"\n\033[38;5;201mErasing {disk} with {passes} passes of {source}...\033[0m\n")
        try:
            for i in range(passes):
                if self.cancelled:
                    break
                    
                print(f"\n\033[38;5;201mPass {i+1} of {passes} with {source}\033[0m")
                
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
                        print(f"\r\033[38;5;201mProgress: \033[38;5;82m{progress:.1f}%\033[0m", end='')
                
                process.wait()
                if process.returncode != 0 and not self.cancelled:
                    raise subprocess.CalledProcessError(process.returncode, process.args)

            if self.cancelled:
                print("\n\033[38;5;201mSecure erase cancelled\033[0m")
            else:
                print(f"\n\033[38;5;82mSecure erase completed successfully with {passes} passes\033[0m")
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            print(f"\n\033[38;5;201mSecure erase failed: {error_msg}\033[0m")

    def create_disk_image(self):
        print("\n\033[38;5;201mCreate Disk Image\033[0m")
        print(" ")
        
        disk = self.select_disk("Select disk to create image from")
        if not disk:
            return
            
        # Prompt for save path
        save_path = input("\033[38;5;82mEnter directory to save image: \033[0m").strip()
        if not save_path or not os.path.isdir(save_path):
            print("\033[38;5;201mInvalid directory path\033[0m")
            return
            
        # Prompt for filename
        default_name = f"disk_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
        filename = input(f"\033[38;5;82mEnter filename for image (default: {default_name}): \033[0m").strip()
        if not filename:
            filename = default_name
            
        self.image_path = os.path.join(save_path, filename)
        
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
            print(f"\033[38;5;201mError: Failed to get disk size: {e}\033[0m")
            return
            
        print(f"\n\033[38;5;201mCreating disk image from {disk} to {self.image_path}...\033[0m\n")
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
                    print(f"\r\033[38;5;201mProgress: \033[38;5;82m{progress_percentage:.1f}%\033[0m", end='')
            
            process.wait()
            if self.cancelled:
                print("\n\033[38;5;201mDisk imaging cancelled\033[0m")
            elif process.returncode == 0:
                print(f"\n\033[38;5;82mDisk image created successfully at:\n{self.image_path}\033[0m")
            else:
                raise subprocess.CalledProcessError(process.returncode, process.args)
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            # Remove failed image file if it exists
            if os.path.exists(self.image_path):
                os.remove(self.image_path)
            print(f"\n\033[38;5;201mDisk imaging failed: {error_msg}\033[0m")

    def create_virtual_disk(self):
        print("\n\033[38;5;201mCreate Virtual Disk\033[0m")
        print(" ")
        
        # Prompt for save path
        save_path = input("\033[38;5;82mEnter directory to save virtual disk: \033[0m").strip()
        if not save_path or not os.path.isdir(save_path):
            print("\033[38;5;201mInvalid directory path\033[0m")
            return
            
        # Prompt for filename
        default_name = f"virtual_disk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
        filename = input(f"\033[38;5;82mEnter filename for virtual disk (default: {default_name}): \033[0m").strip()
        if not filename:
            filename = default_name
            
        image_path = os.path.join(save_path, filename)
        
        # Prompt for size
        while True:
            size_input = input("\033[38;5;82mEnter size of virtual disk (e.g., 1G, 500M): \033[0m").strip().upper()
            if not size_input:
                print("\033[38;5;201mSize cannot be empty!\033[0m")
                continue
                
            try:
                # Validate size format (number followed by M or G)
                size_num = int(size_input[:-1])
                size_unit = size_input[-1]
                if size_unit not in ['M', 'G']:
                    raise ValueError
                break
            except (ValueError, IndexError):
                print("\033[38;5;201mInvalid size format. Use format like 1G or 500M\033[0m")
                continue
                
        if not self.confirm_operation(
            f"You are about to create a virtual disk with these details:\n"
            f"Path: {image_path}\n"
            f"Size: {size_input}\n"
        ):
            return
            
        print(f"\n\033[38;5;201mCreating virtual disk at {image_path} with size {size_input}...\033[0m\n")
        try:
            # Create empty file
            subprocess.run(
                ["sudo", "dd", "if=/dev/zero", f"of={image_path}", "bs=1", f"count=0", f"seek={size_input}"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Mount as loop device
            result = subprocess.run(
                ["sudo", "losetup", "-f", "--show", image_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            loop_device = result.stdout.strip()
            print(f"\033[38;5;82mVirtual disk created at {image_path} and mounted as {loop_device}\033[0m")
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            # Remove failed image file if it exists
            if os.path.exists(image_path):
                os.remove(image_path)
            print(f"\n\033[38;5;201mFailed to create virtual disk: {error_msg}\033[0m")

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
        print("\n\033[38;5;201mDD Utility - CLI \033[0m")
        print(" ")
        print("\033[38;5;201m1.\033[0m \033[38;5;82mFile to Disk\033[0m")
        print("\033[38;5;201m2.\033[0m \033[38;5;82mDisk to Disk\033[0m")
        print("\033[38;5;201m3.\033[0m \033[38;5;82mCreate Partition Table\033[0m")
        print("\033[38;5;201m4.\033[0m \033[38;5;82mFormat Disk/Partition\033[0m")
        print("\033[38;5;201m5.\033[0m \033[38;5;82mSecure Erase Disk\033[0m")
        print("\033[38;5;201m6.\033[0m \033[38;5;82mCreate Disk Image\033[0m")
        print("\033[38;5;201m7.\033[0m \033[38;5;82mCreate Virtual Disk\033[0m")
        print("\033[38;5;201m8.\033[0m \033[38;5;82mList Disks\033[0m")
        print("\033[38;5;201m9.\033[0m \033[38;5;82mExit\033[0m")
        
        choice = input("\n\033[38;5;82mSelect operation \033[0m\033[38;5;201m(1-9)\033[0m\033[38;5;82m: \033[0m").strip()
        
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
                utility.create_virtual_disk()
            elif choice == '8':
                utility.list_disks()
            elif choice == '9':
                print("\033[38;5;201mExiting...\033[0m")
                break
            else:
                print("\033[38;5;201mInvalid choice. Please try again.\033[0m")
        except KeyboardInterrupt:
            print("\n\033[38;5;201mOperation cancelled by user\033[0m")
            utility.cancel_operation()
        except Exception as e:
            print(f"\n\033[38;5;201mError: {e}\033[0m")

if __name__ == "__main__":
    main()
