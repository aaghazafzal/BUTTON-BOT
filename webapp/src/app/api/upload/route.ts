import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as Blob;
    const type = formData.get('type') as string; // 'photo', 'video', 'document'
    
    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
    }

    if (file.size > 20 * 1024 * 1024) { // 20MB limit for Web App uploads
      return NextResponse.json({ error: 'File too large. Max 20MB allowed.' }, { status: 400 });
    }

    const botToken = process.env.BOT_TOKEN;
    const binChannel = process.env.BIN_CHANNEL_ID;

    if (!botToken || !binChannel) {
      return NextResponse.json({ error: 'Bot token or Bin channel not configured' }, { status: 500 });
    }

    const tgFormData = new FormData();
    tgFormData.append('chat_id', binChannel);
    
    // For telegram API, we send it as 'photo', 'video', or 'document' field
    const fieldName = type === 'photo' ? 'photo' : type === 'video' ? 'video' : 'document';
    tgFormData.append(fieldName, file);

    const method = type === 'photo' ? 'sendPhoto' : type === 'video' ? 'sendVideo' : 'sendDocument';
    const tgResponse = await fetch(`https://api.telegram.org/bot${botToken}/${method}`, {
      method: 'POST',
      body: tgFormData
    });

    const tgData = await tgResponse.json();

    if (!tgData.ok) {
      console.error("TG API Error:", tgData);
      return NextResponse.json({ error: 'Failed to upload to Telegram' }, { status: 500 });
    }

    // Extract file_id from message
    const msg = tgData.result;
    let fileId = '';
    
    if (type === 'photo') {
      // get highest quality photo
      fileId = msg.photo[msg.photo.length - 1].file_id;
    } else if (type === 'video') {
      fileId = msg.video.file_id;
    } else {
      fileId = msg.document.file_id;
    }

    return NextResponse.json({ fileId, messageId: msg.message_id });

  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
