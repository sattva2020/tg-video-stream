const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const texturesDir = path.join(__dirname, '../public/textures');
const files = fs.readdirSync(texturesDir);

files.forEach(file => {
  if (file.endsWith('.jpg') || file.endsWith('.png')) {
    const inputPath = path.join(texturesDir, file);
    const outputPath = path.join(texturesDir, file.replace(/\.(jpg|png)$/, '.webp'));

    sharp(inputPath)
      .webp({ quality: 80 })
      .toFile(outputPath)
      .then(info => {
        console.log(`Converted ${file} to WebP: ${info.size} bytes`);
      })
      .catch(err => {
        console.error(`Error converting ${file}:`, err);
      });
  }
});
