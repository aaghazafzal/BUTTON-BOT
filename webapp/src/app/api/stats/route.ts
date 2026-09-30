import { NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import { Post, Project } from '@/lib/models';
import mongoose from 'mongoose';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get('userId');

  if (!userId) {
    return NextResponse.json({ error: 'Missing userId' }, { status: 400 });
  }

  try {
    await connectToDatabase();

    const postCount = await Post.countDocuments({ user_id: Number(userId) });
    const projectCount = await Project.countDocuments({ user_id: Number(userId) });

    // Aggregate total clicks (requires access to post_buttons or post_reactions, 
    // for now we'll just mock it or query the buttons collection if mapped)
    const db = mongoose.connection.db;
    let totalClicks = 0;
    
    if (db) {
       // Find all post IDs for this user
       const userPosts = await Post.find({ user_id: Number(userId) }, { id: 1 }).lean();
       const postIds = userPosts.map(p => p.id);
       
       if (postIds.length > 0) {
         // Sum reactions
         const reactions = await db.collection('post_reactions').find({ post_id: { $in: postIds } }).toArray();
         totalClicks += reactions.length;
       }
    }

    return NextResponse.json({
      postCount,
      projectCount,
      totalClicks
    });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
