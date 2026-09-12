import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const src='D:/Onyx/Onyx_SIH2026_Remade.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(src));
console.log((await p.inspect({kind:'slide,textbox,shape,notes,layout',maxChars:12000})).ndjson);
const m=await p.export({format:'webp',montage:true,scale:1}); await fs.writeFile('D:/Onyx/Onyx_montage.webp',new Uint8Array(await m.arrayBuffer()));
for (const [i,s] of p.slides.items.entries()){const o=await s.export({format:'png',scale:1}); await fs.writeFile(`D:/Onyx/onyx-slide-${i+1}.png`,new Uint8Array(await o.arrayBuffer()));}
