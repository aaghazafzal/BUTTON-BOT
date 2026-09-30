import { NextResponse } from 'next/server';
import connectToDatabase, { getNextId } from '@/lib/mongodb';
import { Post } from '@/lib/models';
import mongoose from 'mongoose';

export async function POST(request: Request) {
  try {
    const data = await request.json();
    const { userId, title, contentType, content, caption, buttons } = data;

    if (!userId || !contentType || !content) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    await connectToDatabase();
    const db = mongoose.connection.db;
    if (!db) throw new Error("Database not connected");

    // 1. Get custom ID for post
    const postId = await getNextId("posts");
    const now = new Date();

    // 2. Insert Post (matches Python bot structure)
    await db.collection('posts').insertOne({
      _id: postId as any,
      user_id: Number(userId),
      content_type: contentType,
      content: content,
      caption: caption || null,
      title: title || null,
      parse_mode: "HTML",
      created_at: now,
      updated_at: now,
    });

    // 3. Initialize Reaction Counts
    await db.collection('reaction_counts').updateOne(
      { _id: postId as any },
      { $setOnInsert: { likes: 0, dislikes: 0, views: 0, shares: 0 } },
      { upsert: true }
    );

    // 4. Insert Buttons if provided
    if (buttons && Array.isArray(buttons) && buttons.length > 0) {
      const buttonDocs = buttons.map((btn: any) => ({
        post_id: postId,
        row_num: btn.row_num,
        order_num: btn.order_num,
        button_type: btn.button_type,
        text: btn.text,
        url: btn.url || null,
        color: btn.color || 'default'
      }));
      await db.collection('buttons').insertMany(buttonDocs);
    }

    return NextResponse.json({ success: true, postId });
  } catch (error) {
    console.error('Create Post Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
