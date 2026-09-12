import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const src = String.raw`C:\Users\Ronit Sharma\Downloads\Problem Statement ID – Problem Statement Title- Theme- PS Category- SoftwareHardware Team ID- Team Name (Registered on portal).pptx`;
const p = await PresentationFile.importPptx(await FileBlob.load(src));
console.log((await p.inspect({kind:"slide,textbox,shape,image,table,chart,notes,layout",maxChars:30000})).ndjson);
console.log('slides',p.slides.items.length);
for (const [i,s] of p.slides.items.entries()) { const out=await s.export({format:'png',scale:1}); await (await import('node:fs/promises')).writeFile(`source-${i+1}.png`,new Uint8Array(await out.arrayBuffer())); }
