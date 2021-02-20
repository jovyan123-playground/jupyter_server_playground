import hashlib
import os
import shlex
import subprocess

version = "1.5.0"

BUF_SIZE = 65536

cmd = f'git commit -am "Publish {version}" -m "SHA256 hashes:"'

for fname in os.listdir('dist'):
    sha256 = hashlib.sha256()

    with open(os.path.join('dist', fname), 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    sha256 = sha256.hexdigest()
    print(fname, sha256)
    cmd += f' -m "{fname}: {sha256}"'

print(cmd)
subprocess.run(shlex.split(cmd))
# const files = fs.readdirSync(distDir);
# const hashes = new Map<string, string>();
# files.forEach(file => {
#     const shasum = crypto.createHash('sha256');
#     const hash = shasum.update(fs.readFileSync(path.join(distDir, file)));
#     hashes.set(file, hash.digest('hex'));
# });

# const hashString = Array.from(hashes.entries())
#     .map(entry => `${entry[0]}: ${entry[1]}`)
#     .join('" -m "');

# // Make the commit and the tag.
# const curr = utils.getPythonVersion();
# utils.run(
#     `git commit -am "Publish ${curr}" -m "SHA256 hashes:" -m "${hashString}"`
# );
