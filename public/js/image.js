async function loadImageElement(file) {
  if ('createImageBitmap' in window) {
    try {
      return await createImageBitmap(file);
    } catch {
      /* 继续使用 Image 兜底 */
    }
  }
  return new Promise((resolve, reject) => {
    const image = new Image();
    const url = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('这张图片暂时无法读取，请换一张试试'));
    };
    image.src = url;
  });
}

/**
 * 将本地图片压缩为 JPEG data URL。
 * @param {File} file
 * @param {{maxSize?: number, square?: boolean, quality?: number}} options
 */
export async function compressImageFile(file, { maxSize = 1600, square = false, quality = 0.86 } = {}) {
  if (!file || !file.type.startsWith('image/')) throw new Error('请选择图片文件');
  if (file.size > 15 * 1024 * 1024) throw new Error('图片不能超过 15MB');

  const image = await loadImageElement(file);
  const width = image.width || image.naturalWidth;
  const height = image.height || image.naturalHeight;
  if (!width || !height) throw new Error('图片尺寸读取失败');

  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  context.fillStyle = '#f6faf7';

  if (square) {
    const side = Math.min(width, height);
    const sourceX = (width - side) / 2;
    const sourceY = (height - side) / 2;
    const target = Math.min(maxSize, 720);
    canvas.width = target;
    canvas.height = target;
    context.fillRect(0, 0, target, target);
    context.drawImage(image, sourceX, sourceY, side, side, 0, 0, target, target);
  } else {
    const ratio = Math.min(1, maxSize / Math.max(width, height));
    canvas.width = Math.max(1, Math.round(width * ratio));
    canvas.height = Math.max(1, Math.round(height * ratio));
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
  }

  if (typeof image.close === 'function') image.close();
  return canvas.toDataURL('image/jpeg', quality);
}
