import path from 'node:path';
import { pathToFileURL } from 'node:url';
const SKILL_DIR=String.raw`C:\Users\Ronit Sharma\.codex\plugins\cache\openai-primary-runtime\presentations\26.904.11930\skills\presentations`;
const workspaceDir='D:/Onyx'; const candidatePath='D:/Onyx/Onyx_SIH2026_Remade.pptx'; const finalPath='D:/Onyx/final/Onyx_SIH2026_Final.pptx';
const { finalizePresentation }=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir,candidatePath,finalPath,pythonExecutable:String.raw`C:\Users\Ronit Sharma\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`,integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','18288020,10287000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:'D:/Onyx/.codex-finalizer/Onyx_SIH2026_Final.validation.json'});
console.log(JSON.stringify(result,null,2));
