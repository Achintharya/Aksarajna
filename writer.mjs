import fs from 'fs';
import * as readline from 'readline';
import ollama from 'ollama';


const CONTEXT_FILE = "./context.txt"; // Context file
const WRITING_STYLE_FILE = "./writing_style.txt"; // Full article for style reference

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

let articleCount = 0; // Initialize article count

// Main input loop
async function processInput() {
  rl.question("Enter your query (or type 'exit' to quit):\n", async (input) => {
    if (input.toLowerCase() === 'exit') {
      rl.close();
      return;
    }

    if (!input.trim()) {
      console.log("Please enter a valid input.");
      processInput();
      return;
    }

    try {
      const context = fs.readFileSync(CONTEXT_FILE, "utf-8");
      const writingStyle = fs.readFileSync(WRITING_STYLE_FILE, "utf-8");

      if (!context) {
        console.log("No relevant context found. Proceeding with minimal guidance.");
      }

      const response = await generateChatResponse(writingStyle, context || "", input);

      // Increment the article count and write the response to a new file
      articleCount++;
      const articleFileName = `article${articleCount}.txt`;
      fs.writeFileSync(articleFileName, response, "utf-8");
      console.log(`The article has been saved to '${articleFileName}'.`);
    } catch (error) {
      console.error("An error occurred:", error.message);
    } finally {
      processInput();
    }
  });
}


// Generate a response using Mistral
async function generateChatResponse(writingStyle, context, query) {
  const currentDate = new Date().toLocaleDateString();
  const currentTime = new Date().toLocaleTimeString();
  const promptMessage = `Current Date and Time: ${currentDate}, ${currentTime}
Writing Style Example: ${writingStyle}
Context: ${context}`;

  try {
    const response = await ollama.chat({
      model: 'llava',
      messages: [
        { role: "system", content: "### You are an AI that imitates a writing style(without including any info from it) to write about the context provided. ###" },
        { role: "user", content: promptMessage }
      ],
    });

    return response.message.content;

  } catch (error) {
    console.error("Error generating response:", error.message);
    return "Sorry, I couldn't process your request.";
  }
}

// Start the input loop
processInput();
