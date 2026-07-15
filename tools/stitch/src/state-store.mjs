import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export function emptyGenerationState() {
  return {
    projectId: null,
    projectTitle: "AI Couple Dish - Couple Cosmos",
    screens: {}
  };
}

export async function readGenerationState(filePath) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      return emptyGenerationState();
    }
    throw error;
  }
}

export async function writeGenerationState(filePath, state) {
  await mkdir(dirname(filePath), { recursive: true });
  const temporaryPath = filePath + ".tmp";
  await writeFile(
    temporaryPath,
    JSON.stringify(state, null, 2) + String.fromCharCode(10)
  );
  await rename(temporaryPath, filePath);
}
