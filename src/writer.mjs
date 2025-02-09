import fs from 'fs';
import * as readline from 'readline';
import ollama from 'ollama';


const CONTEXT_FILE = "data/context.txt"; // Context file
const WRITING_STYLE_FILE = "data/writing_style.txt"; // Full article for style reference


// Function to save the article to a file
function saveArticleToFile(response, fileName) {
  fs.writeFileSync(fileName, response, "utf-8");
  console.log(`The article has been saved to '${fileName}'.`);
}

async function start() {
  try {
    const context = fs.readFileSync(CONTEXT_FILE, "utf-8");
    const writingStyle = fs.readFileSync(WRITING_STYLE_FILE, "utf-8");

    if (!context) {
      console.log("No relevant context found. Proceeding with minimal guidance.");
    }

    // Directly define the query here
    const query = "Write brief informative article "; // Replace with your actual query

    const response = await generateChatResponse(writingStyle, context || "", query);

    // Prompt user for the file name
    const fileName = await promptForFileName(); // New function to get file name
    saveArticleToFile(response, fileName); 

  } catch (error) {
    console.error("An error occurred:", error.message);
  }
}

// New function to prompt for file name
async function promptForFileName() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question('Enter the file name to save the article: ', (fileName) => {
      rl.close();
      resolve(`${fileName}.txt`); // Append .txt extension
    });
  });
}

// Generate a response using Mistral
async function generateChatResponse(writingStyle, context, query) {
  const currentDate = new Date().toLocaleDateString();
  const currentTime = new Date().toLocaleTimeString();
  const promptMessage = `Current Date and Time: ${currentDate}, ${currentTime}
Writing Style Example: ${writingStyle}
Context: ${context}
User Query: ${query}`;

  try {
    const response = await ollama.chat({
      model: 'mistral',
      messages: [
        { role: "system", content: "### You are an AI that imitates a writing style (without including any info from it) to write nonredundantly about the context provided. ###" },
        { role: "user", content: promptMessage }
      ],
    });

    console.log(response.message.content);
    return response.message.content;

  } catch (error) {
    console.error("Error generating response:", error.message);
    return "Sorry, I couldn't process your request.";
  }
}

// Start the process
start();
