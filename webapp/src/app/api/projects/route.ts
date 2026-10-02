import { NextResponse } from 'next/server';
import connectToDatabase, { getNextId } from '@/lib/mongodb';
import { Project } from '@/lib/models';
import mongoose from 'mongoose';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get('userId');

  if (!userId) {
    return NextResponse.json({ error: 'Missing userId' }, { status: 400 });
  }

  try {
    await connectToDatabase();
    
    // Find projects for user, sort by latest
    const projects = await Project.find({ user_id: Number(userId) })
      .sort({ created_at: -1 })
      .lean();

    const formatted = projects.map(p => ({
      ...p,
      id: p._id
    }));

    return NextResponse.json({ projects: formatted });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const data = await request.json();
    const { projectId, userId, channelId, channelTitle, buttonsJson, isActive } = data;

    if (!userId || !channelId || !channelTitle || !buttonsJson) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    await connectToDatabase();
    const db = mongoose.connection.db;
    if (!db) throw new Error("Database not connected");

    const now = new Date();

    if (projectId) {
      // Update existing project
      await db.collection('channel_projects').updateOne(
        { _id: Number(projectId), user_id: Number(userId) },
        {
          $set: {
            channel_id: channelId,
            channel_title: channelTitle,
            buttons_json: buttonsJson,
            is_active: isActive !== undefined ? isActive : true,
          }
        }
      );
      return NextResponse.json({ success: true, projectId });
    } else {
      // Create new project
      // Check if channel already exists
      const existing = await db.collection('channel_projects').findOne({ channel_id: channelId });
      if (existing) {
        // Update existing instead of creating duplicate for the same channel
        await db.collection('channel_projects').updateOne(
          { channel_id: channelId },
          {
            $set: {
              user_id: Number(userId),
              channel_title: channelTitle,
              buttons_json: buttonsJson,
              is_active: isActive !== undefined ? isActive : true,
              created_at: now
            }
          }
        );
        return NextResponse.json({ success: true, projectId: existing._id });
      } else {
        const newId = await getNextId("channel_projects");
        await db.collection('channel_projects').insertOne({
          _id: newId as any,
          user_id: Number(userId),
          channel_id: channelId,
          channel_title: channelTitle,
          buttons_json: buttonsJson,
          is_active: isActive !== undefined ? isActive : true,
          created_at: now
        });
        return NextResponse.json({ success: true, projectId: newId });
      }
    }
  } catch (error) {
    console.error('Create Project Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const data = await request.json();
    const { projectId, userId } = data;

    if (!projectId || !userId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    await connectToDatabase();
    const db = mongoose.connection.db;
    if (!db) throw new Error("Database not connected");

    await db.collection('channel_projects').deleteOne({
      _id: Number(projectId),
      user_id: Number(userId)
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete Project Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
