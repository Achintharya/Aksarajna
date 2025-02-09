import fs from 'fs';
import * as readline from 'readline';
import ollama from 'ollama';


const CONTEXT_FILE = "./data/context.txt"; // Context file
const WRITING_STYLE_FILE = "./data/writing_style.txt"; // Full article for style reference

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

let lastResponse = ""; // Variable to store the last response

// Function to save the article to a file
function saveArticleToFile(response, fileName) {
  fs.writeFileSync(fileName, response, "utf-8");
  console.log(`The article has been saved to '${fileName}'.`);
}

async function start() {
  try {
    const context = fs.readFileSync(CONTEXT_FILE, "utf-8");
    processInput(context);
  } catch (error) {
    console.error("Error reading context file:", error.message);
  }
}

// Main input loop
async function processInput(context) {
  rl.question("==>  ", async (input) => {
    if (input.toLowerCase() === 'exit') {
      rl.close();
      return;
    }

    if (!input.trim()) {
      console.log("Please enter a valid input.");
      processInput(context);
      return;
    }

    // Check if the input is a save command with a file name
    const saveCommandMatch = input.match(/^save to file as "(.+)"$/i);
    if (saveCommandMatch) {
      const fileName = `./articles/${saveCommandMatch[1]}.txt`;
      if (lastResponse) {
        saveArticleToFile(lastResponse, fileName);
      } else {
        console.log("No previous response to save.");
      }
    } else {
      try {
        const writingStyle = fs.readFileSync(WRITING_STYLE_FILE, "utf-8");

        if (!context) {
          console.log("No relevant context found. Proceeding with minimal guidance.");
        }

        const response = await generateChatResponse(writingStyle, context || "", input);

        // Update lastResponse with the current response
        lastResponse = response;

      } catch (error) {
        console.error("An error occurred:", error.message);
      }
    }

    processInput(context);
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

// Start the input loop
start();
