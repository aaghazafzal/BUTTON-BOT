import { NextResponse } from 'next/server';
import connectToDatabase from '@/lib/mongodb';
import { Post, Project, User } from '@/lib/models';
import mongoose from 'mongoose';

const FREE_MAX_POSTS = 100;

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

    const db = mongoose.connection.db;
    let totalClicks = 0;
    
    if (db) {
       const userPosts = await Post.find({ user_id: Number(userId) }, { id: 1 }).lean();
       const postIds = userPosts.map(p => p.id);
       
       if (postIds.length > 0) {
         const reactions = await db.collection('post_reactions').find({ post_id: { $in: postIds } }).toArray();
         totalClicks += reactions.length;
       }
    }

    // Get user premium info
    const user = await User.findOne({ user_id: Number(userId) }).lean();
    let isPremiumActive = false;
    let maxPosts = FREE_MAX_POSTS;
    
    if (user) {
      const now = new Date();
      if (user.premium_expiry && new Date(user.premium_expiry) > now) {
        isPremiumActive = true;
      }
      maxPosts = FREE_MAX_POSTS + (user.premium_posts_added || 0);
    }
    
    // Admins (replace with OWNER_IDS check if available via env, else just rely on UI)
    // For now, if maxPosts is huge, they might be admin, but we'll stick to actual DB values.

    return NextResponse.json({
      postCount,
      projectCount,
      totalClicks,
      isPremiumActive,
      maxPosts
    });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
