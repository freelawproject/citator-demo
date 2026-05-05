const fs = require('fs');
const path = require('path');

module.exports = function () {
  const dir = path.join(__dirname, 'opinions');
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')));
};
